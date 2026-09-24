"""Agenda o backup diário do banco SEM o Agendador de Tarefas do Windows.

Roda como serviço do nssm (HMPCF-Backup-Svc, conta LocalSystem) e chama o
mesmo backup_postgres.bat de sempre:
  - todo dia a partir das 23:00, uma vez por dia;
  - ao ligar, se o último backup tem mais de 26 h (PC desligado às 23:00),
    faz na hora;
  - se existir C:\\HMPCF\\backups\\RODAR_AGORA, faz no próximo minuto e apaga o arquivo.

Por que existe: em 24/09/2026 o Agendador de Tarefas do servidor parou de
executar tarefas (o backup das 23:00 não rodou) e reiniciar o PC da recepção
é complicado. O serviço não enxerga o G: do Google Drive (acesso negado para
outra conta), então a cópia na nuvem vai pela pasta C:\\HMPCF\\backups_nuvem,
que o app do Google Drive sincroniza ("Pastas do computador").

Só biblioteca padrão. Instalação: instalar_servico_backup.ps1 (mesma pasta).
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PASTA = Path(r"C:\HMPCF\backups")
BAT = Path(__file__).resolve().with_name("backup_postgres.bat")
ESTADO = PASTA / "agendador_backup.json"
GATILHO = PASTA / "RODAR_AGORA"  # criar esse arquivo (vazio) = backup no próximo minuto
HORA = 23
ATRASO_MAXIMO = timedelta(hours=26)


def log(msg: str) -> None:
    print(f"{datetime.now():%d/%m/%Y %H:%M:%S} {msg}", flush=True)


def ultimo_dia_feito() -> str:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8")).get("dia", "")
    except (OSError, ValueError):
        return ""


def backup_mais_novo() -> datetime | None:
    arquivos = list(PASTA.glob("hmpcf_*.sql.enc"))
    if not arquivos:
        return None
    return datetime.fromtimestamp(max(a.stat().st_mtime for a in arquivos))


def rodar_backup(motivo: str) -> None:
    log(f"Iniciando backup ({motivo})")
    r = subprocess.run(["cmd.exe", "/c", str(BAT)], cwd=BAT.parent)
    log(f"Backup terminou com código {r.returncode} (detalhes em {PASTA / 'backup.log'})")
    PASTA.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps({"dia": f"{datetime.now():%Y-%m-%d}", "codigo": r.returncode,
                                  "quando": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")


def main() -> None:
    log(f"Agendador de backup ligado — todo dia às {HORA}:00 ({BAT})")
    ultimo = backup_mais_novo()
    if ultimo is None or datetime.now() - ultimo > ATRASO_MAXIMO:
        rodar_backup("atrasado: último backup " + (f"{ultimo:%d/%m %H:%M}" if ultimo else "nenhum"))
    while True:
        agora = datetime.now()
        if GATILHO.exists():
            GATILHO.unlink(missing_ok=True)
            rodar_backup("pedido manual (RODAR_AGORA)")
        elif agora.hour >= HORA and ultimo_dia_feito() != f"{agora:%Y-%m-%d}":
            rodar_backup("horário das 23:00")
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
