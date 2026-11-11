"""Avisa no Telegram quando o sistema cai ou o backup atrasa.

Roda como serviço do nssm (HMPCF-Monitor-Svc, LocalSystem), como o agendador
do backup -- o Agendador de Tarefas do Windows deste servidor não é confiável
(ver agendador_backup.py). A cada 5 minutos confere:
  - sistema: GET http://127.0.0.1:8001/health
  - banco:   porta 5432 do PostgreSQL aceitando conexão
  - backup:  mesma regra da faixa do Painel (app/services/backup_status.py)

Avisa quando algo cai (sistema/banco: 2 checagens seguidas, ~10 min, pra não
avisar por causa de um reinício) e de novo quando volta. Todo dia às 07:30
manda um resumo "tudo certo" -- se o servidor inteiro desligar, o monitor
desliga junto; a falta do resumo da manhã é o aviso desse caso.

Mensagens só com situação do sistema, nunca dado de paciente.
Configuração em C:\\HMPCF\\telegram.env (fora do repositório):
  TELEGRAM_TOKEN=...   (do @BotFather)
  TELEGRAM_CHAT=...    (id do grupo dos avisos)
Teste: python monitor.py --teste   (manda uma mensagem e sai)
"""
import json
import socket
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.services.backup_status import situacao_backup  # noqa: E402

CONFIG = Path(r"C:\HMPCF\telegram.env")
ESTADO = Path(r"C:\HMPCF\monitor_estado.json")
PASTA_BACKUP = Path(r"C:\HMPCF\backups")
HEALTH = "http://127.0.0.1:8001/health"
INTERVALO_S = 5 * 60
FALHAS_PARA_AVISAR = 2
HORA_RESUMO = (7, 30)
FUSO = ZoneInfo("America/Sao_Paulo")


def log(msg: str) -> None:
    print(f"{datetime.now():%d/%m/%Y %H:%M:%S} {msg}", flush=True)


def ler_config() -> dict:
    cfg = {}
    for linha in CONFIG.read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, v = linha.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def enviar(texto: str) -> bool:
    try:
        cfg = ler_config()
        dados = urllib.parse.urlencode({"chat_id": cfg["TELEGRAM_CHAT"], "text": texto}).encode()
        url = f"https://api.telegram.org/bot{cfg['TELEGRAM_TOKEN']}/sendMessage"
        with urllib.request.urlopen(url, data=dados, timeout=20) as r:
            return json.load(r).get("ok", False)
    except Exception as e:  # sem internet, token errado... tenta de novo no próximo ciclo
        log(f"Falha ao mandar aviso no Telegram: {type(e).__name__}")
        return False


def sistema_no_ar() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=10) as r:
            return json.load(r).get("status") == "ok"
    except Exception:
        return False


def banco_no_ar() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=5):
            return True
    except OSError:
        return False


def problema_backup(agora: datetime) -> str:
    """'' se o backup está em dia; senão, o que há de errado (texto curto)."""
    s = situacao_backup(PASTA_BACKUP, agora)
    if s["situacao"] == "ok":
        return ""
    if s["situacao"] == "sem_backup":
        return "nenhum backup encontrado"
    if s["situacao"] == "atrasado":
        return f"último backup há {s['horas']:.0f} h (deveria ser todo dia às 23:00)"
    execucao = s.get("execucao") or {}
    return "o último backup não terminou ou não foi para a nuvem" + (
        f" ({execucao['problema']})" if execucao.get("problema") else "")


def carregar_estado() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def salvar_estado(estado: dict) -> None:
    ESTADO.write_text(json.dumps(estado), encoding="utf-8")


def conferir(item: str, ok: bool, estado: dict, quando: str, texto_caiu: str, texto_voltou: str) -> None:
    """Conta falhas seguidas; avisa na N-ésima e avisa de novo quando volta."""
    falhas = 0 if ok else estado.get(f"{item}_falhas", 0) + 1
    estado[f"{item}_falhas"] = falhas
    avisado = estado.get(f"{item}_avisado", False)
    if falhas >= FALHAS_PARA_AVISAR and not avisado:
        if enviar(f"🔴 HMPCF: {texto_caiu} (confirmado às {quando}, ~10 min fora).\n"
                  "Ver docs\\RECUPERACAO_SERVIDOR.md no servidor."):
            estado[f"{item}_avisado"] = True
    elif ok and avisado:
        if enviar(f"🟢 HMPCF: {texto_voltou}."):
            estado[f"{item}_avisado"] = False


def ciclo(estado: dict) -> None:
    agora = datetime.now(FUSO)
    hora = f"{agora:%H:%M}"
    sistema, banco = sistema_no_ar(), banco_no_ar()
    conferir("sistema", sistema, estado, hora,
             "o sistema não está respondendo", "o sistema voltou a responder")
    conferir("banco", banco, estado, hora,
             "o banco de dados (PostgreSQL) não está respondendo", "o banco de dados voltou")

    backup = problema_backup(agora)
    if backup and estado.get("backup_avisado_dia") != f"{agora:%Y-%m-%d}":
        if enviar(f"🟠 HMPCF: backup com problema — {backup}.\nVer o Painel (TI) e C:\\HMPCF\\backups\\backup.log."):
            estado["backup_avisado_dia"] = f"{agora:%Y-%m-%d}"  # no máximo 1 aviso por dia
    elif not backup and estado.get("backup_avisado_dia"):
        if enviar("🟢 HMPCF: backup em dia de novo."):
            estado.pop("backup_avisado_dia")

    if (agora.hour, agora.minute) >= HORA_RESUMO and estado.get("resumo_dia") != f"{agora:%Y-%m-%d}":
        partes = [
            "sistema no ar" if sistema else "sistema FORA DO AR",
            "banco no ar" if banco else "banco FORA DO AR",
            "backup em dia" if not backup else f"backup: {backup}",
        ]
        tudo_ok = sistema and banco and not backup
        if enviar(f"{'✅' if tudo_ok else '⚠️'} HMPCF bom dia: " + ", ".join(partes) + "."):
            estado["resumo_dia"] = f"{agora:%Y-%m-%d}"

    log(f"sistema={'ok' if sistema else 'FALHOU'} banco={'ok' if banco else 'FALHOU'} "
        f"backup={'ok' if not backup else backup}")


def main() -> None:
    log("Monitor do HMPCF ligado — confere a cada 5 min e avisa no Telegram")
    estado = carregar_estado()
    while True:
        try:
            ciclo(estado)
            salvar_estado(estado)
        except Exception as e:  # o monitor nunca pode parar por um erro dele mesmo
            log(f"Erro no monitor: {type(e).__name__}: {e}")
        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    if "--teste" in sys.argv:
        ok = enviar("✅ HMPCF: teste do monitor — os avisos do servidor vão chegar aqui.")
        print("mensagem enviada" if ok else "FALHOU (ver token e TELEGRAM_CHAT em C:\\HMPCF\\telegram.env)")
        sys.exit(0 if ok else 1)
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
