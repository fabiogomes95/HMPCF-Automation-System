"""Migração automática do dia: na primeira vez que o BPA liga ou é aberto no
dia, leva pro Firebird deste notebook os pacientes atendidos na recepção nos
últimos JANELA_DIAS dias (cobre a virada do mês). Mesma rotina da migração
manual — quem já está no Firebird é ignorado, então rodar de novo não duplica.

Roda numa thread (a tela abre na hora) e guarda o resultado em
bpa/migracao_auto.json, pra não repetir no mesmo dia se o BPA reiniciar."""
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
ARQUIVO = BASE / "migracao_auto.json"

_estado: dict = {"situacao": "nunca"}
_lock_estado = threading.Lock()


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


def executar_se_preciso() -> bool:
    """Dispara a migração do dia em segundo plano, se ainda não rodou hoje.
    Devolve True se disparou agora."""
    if os.getenv("BPA_MIGRACAO_AUTO", "1") == "0":  # desligada (testes)
        return False
    agora = datetime.now()
    if not precisa_rodar(agora):
        return False
    if migracao.TRAVA.locked():  # manual em andamento: tenta na próxima consulta
        return False
    _atualizar(situacao="rodando", data=agora.date().isoformat(), inicio=agora.isoformat(timespec="seconds"),
               fim=None, erro="", i=0, total=0)
    threading.Thread(target=_rodar, name="migracao-auto", daemon=True).start()
    return True


def _rodar() -> None:
    if not migracao.TRAVA.acquire(blocking=False):
        _atualizar(situacao="interrompida", erro="Migração manual em andamento")
        return
    try:
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
            _atualizar(situacao="ok", fim=fim, erro="", **{
                k: final[k] for k in ("inseridos", "atualizados", "duplicatas", "erros", "cpf_invalidos")
            })
        print(f"[BPA] migração automática: {estado()}")
    except Exception as e:  # nunca derrubar o BPA por causa da automática
        _atualizar(situacao="erro", fim=datetime.now().isoformat(timespec="seconds"), erro=str(e))
    finally:
        migracao.TRAVA.release()


_carregar()
