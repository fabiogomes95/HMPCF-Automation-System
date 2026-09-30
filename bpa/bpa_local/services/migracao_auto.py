"""Migração automática do dia: na primeira vez que o BPA liga ou é aberto no
dia, leva pro Firebird deste notebook os pacientes atendidos na recepção nos
últimos JANELA_DIAS dias (cobre a virada do mês). Mesma rotina da migração
manual — quem já está no Firebird é ignorado, então rodar de novo não duplica.

Roda numa thread (a tela abre na hora) e guarda o resultado em
bpa/migracao_auto.json, pra não repetir no mesmo dia se o BPA reiniciar.

Depois da do dia, confere a cada CONFERIR_NOVOS se entrou atendimento novo
(ou foi alterado) na recepção -- ex.: o faturamento lançou uma folha A4 que a
recepção esqueceu -- e, se entrou, roda de novo sozinha, sem migração manual."""
import json
import os
import threading
from datetime import date, datetime, timedelta

from bpa_local import postgres
from bpa_local.config import BASE
from bpa_local.services import migracao

JANELA_DIAS = 40
# Depois de um erro (servidor fora, Firebird fechado), espera antes de tentar de
# novo -- a tela consulta o status a cada 30 s e não pode martelar o servidor.
ESPERA_APOS_ERRO = timedelta(minutes=10)
# De quanto em quanto tempo pergunta ao Postgres se entrou atendimento novo
# (uma consulta leve: MAX do id e do updated_at).
CONFERIR_NOVOS = timedelta(minutes=2)
ARQUIVO = BASE / "migracao_auto.json"

_estado: dict = {"situacao": "nunca"}
_lock_estado = threading.Lock()
# Dispara no máximo uma migração por vez (a do dia e a de "entrou atendimento novo").
_lock_disparo = threading.Lock()
_ultima_conferencia: datetime | None = None


def _carregar() -> None:
    global _estado
    try:
        _estado = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except Exception:
        _estado = {"situacao": "nunca"}
    if _estado.get("situacao") == "rodando":  # BPA fechou no meio: vale como não rodada
        _estado["situacao"] = "interrompida"


def _salvar() -> None:
    try:
        ARQUIVO.write_text(json.dumps(_estado, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"[BPA] não consegui salvar {ARQUIVO.name}: {e}")


def estado() -> dict:
    with _lock_estado:
        return dict(_estado)


def _atualizar(**campos) -> None:
    with _lock_estado:
        _estado.update(campos)
        _salvar()


def precisa_rodar(agora: datetime) -> bool:
    e = estado()
    if e.get("situacao") == "rodando":
        return False
    if e.get("data") == agora.date().isoformat() and e.get("situacao") == "ok":
        return False
    if e.get("situacao") == "erro" and e.get("fim"):
        if agora - datetime.fromisoformat(e["fim"]) < ESPERA_APOS_ERRO:
            return False
    return True


def assinatura_recepcao() -> str:
    """Muda sempre que um atendimento é criado ou alterado na recepção
    (inclusive pelo faturamento/TI numa folha A4)."""
    pg = postgres.conectar()
    try:
        cur = pg.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0), MAX(updated_at) FROM recepcao_atendimentos")
        max_id, max_upd = cur.fetchone()
        return f"{max_id}|{max_upd.isoformat() if max_upd else ''}"
    finally:
        pg.close()


def _disparar(agora: datetime) -> bool:
    """Marca como rodando e começa a migração em segundo plano. Quem chama segura _lock_disparo."""
    if migracao.TRAVA.locked():  # manual em andamento: tenta na próxima consulta
        return False
    _atualizar(situacao="rodando", data=agora.date().isoformat(), inicio=agora.isoformat(timespec="seconds"),
               fim=None, erro="", i=0, total=0)
    threading.Thread(target=_rodar, name="migracao-auto", daemon=True).start()
    return True


def executar_se_preciso() -> bool:
    """Dispara a migração do dia em segundo plano, se ainda não rodou hoje.
    Já rodou: de tempos em tempos confere (em outra thread) se entrou
    atendimento novo e, se entrou, roda de novo. Devolve True se disparou agora."""
    global _ultima_conferencia
    if os.getenv("BPA_MIGRACAO_AUTO", "1") == "0":  # desligada (testes)
        return False
    agora = datetime.now()
    with _lock_disparo:
        if precisa_rodar(agora):
            return _disparar(agora)
        e = estado()
        if e.get("situacao") != "ok" or e.get("data") != agora.date().isoformat():
            return False
        if _ultima_conferencia and agora - _ultima_conferencia < CONFERIR_NOVOS:
            return False
        _ultima_conferencia = agora
    threading.Thread(target=conferir_novos, name="migracao-auto-conferir", daemon=True).start()
    return False


def conferir_novos() -> bool:
    """Roda a migração de novo se a recepção mudou desde a última. Devolve True se disparou."""
    try:
        atual = assinatura_recepcao()
    except Exception:  # servidor fora: confere na próxima
        return False
    with _lock_disparo:
        e = estado()
        if e.get("situacao") != "ok" or e.get("assinatura") == atual:
            return False
        print("[BPA] entrou atendimento novo na recepção: migração automática de novo")
        return _disparar(datetime.now())


def _rodar() -> None:
    if not migracao.TRAVA.acquire(blocking=False):
        _atualizar(situacao="interrompida", erro="Migração manual em andamento")
        return
    try:
        try:
            # Lida ANTES de migrar: atendimento que entrar durante a migração
            # muda a assinatura e faz rodar de novo na próxima conferência.
            assinatura = assinatura_recepcao()
        except Exception:
            assinatura = ""
        hoje = date.today()
        query = postgres.query_pacientes_periodo(hoje - timedelta(days=JANELA_DIAS), hoje + timedelta(days=1))
        final = None
        for ev in migracao.migrar(query):
            if ev["tipo"] == "progresso":
                _atualizar(i=ev["i"], total=ev["total"])
            elif ev["tipo"] == "log" and "total" in ev:
                _atualizar(total=ev["total"])
            elif ev["tipo"] in ("erro", "fim"):
                final = ev
        fim = datetime.now().isoformat(timespec="seconds")
        if final is None or final["tipo"] == "erro":
            _atualizar(situacao="erro", fim=fim, erro=(final or {}).get("msg", "Migração não terminou"))
        else:
            _atualizar(situacao="ok", fim=fim, erro="", assinatura=assinatura, **{
                k: final.get(k, 0) for k in ("inseridos", "duplicatas", "erros", "cpf_invalidos", "sem_documento")
            })
        print(f"[BPA] migração automática: {estado()}")
    except Exception as e:  # nunca derrubar o BPA por causa da automática
        _atualizar(situacao="erro", fim=datetime.now().isoformat(timespec="seconds"), erro=str(e))
    finally:
        migracao.TRAVA.release()


_carregar()
