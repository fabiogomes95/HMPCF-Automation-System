"""Botão "Reimportar planilhas" da aba Entradas (só TI).

Roda scripts/importar_planilhas_recepcao.py num processo separado (leva uns
3 minutos e usa bastante memória — não pode travar o backend). A saída vai pro
log, que a tela mostra enquanto roda. O script já grava tudo numa transação só:
se der erro no meio, a tabela fica como estava.

Pra incluir planilha nova: copiar o .xlsx pra C:\\HMPCF\\planilhas_manuais e
clicar no botão."""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.exceptions import ValidationError

_BACKEND = Path(__file__).resolve().parents[2]
_SCRIPT = _BACKEND / "scripts" / "importar_planilhas_recepcao.py"
_LOG = _BACKEND / "importar_planilhas.log"
PASTA = r"C:\HMPCF\planilhas_manuais"

_processo: Optional[subprocess.Popen] = None
_iniciado_em: Optional[datetime] = None
_iniciado_por: Optional[str] = None


def _rodando() -> bool:
    return _processo is not None and _processo.poll() is None


def iniciar(usuario: str) -> dict:
    global _processo, _iniciado_em, _iniciado_por
    if _rodando():
        raise ValidationError("A importação já está rodando — aguarde terminar.")
    pasta = Path(PASTA)
    if not pasta.is_dir() or not list(pasta.glob("*.xlsx")):
        raise ValidationError(f"Nenhuma planilha .xlsx em {PASTA}.")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    log = open(_LOG, "w", encoding="utf-8")
    _processo = subprocess.Popen(
        [sys.executable, str(_SCRIPT), "--pasta", PASTA],
        cwd=str(_BACKEND), stdout=log, stderr=subprocess.STDOUT, env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    log.close()  # o processo filho tem a própria cópia do arquivo
    _iniciado_em, _iniciado_por = datetime.now(), usuario
    return situacao()


def situacao() -> dict:
    try:
        log = _LOG.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        log = ""
    codigo = None if _processo is None else _processo.poll()
    return {
        "rodando": _rodando(),
        "ok": codigo == 0 if _processo is not None and codigo is not None else None,
        "iniciado_em": _iniciado_em.isoformat(timespec="seconds") if _iniciado_em else None,
        "iniciado_por": _iniciado_por,
        "pasta": PASTA,
        "planilhas": sorted(f.name for f in Path(PASTA).glob("*.xlsx")) if Path(PASTA).is_dir() else [],
        "log": log[-8000:],
    }
