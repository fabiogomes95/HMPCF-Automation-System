"""Inicia o BPA local: http://localhost:8503 (só este PC).

Usado pela tarefa HMPCF-BPA (liga com o Windows), pelo iniciar.bat e pelo
atalho do robozinho."""
import os
import sys

BPA_DIR = os.path.dirname(os.path.abspath(__file__))

# Sem janela (pythonw) o Windows não dá stdout/stderr ao processo e o uvicorn
# quebra ao configurar o log -- manda tudo pra bpa/bpa_local.log.
if sys.stdout is None or sys.stderr is None:
    _log = open(os.path.join(BPA_DIR, "bpa_local.log"), "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = _log

# bpa/ no caminho: os módulos de domínio (bpa_gerador, conferencia,
# fechamento_mes) ficam aqui, fora do pacote bpa_local.
sys.path.insert(0, BPA_DIR)

import socket  # noqa: E402

import uvicorn  # noqa: E402

from bpa_local.config import PORTA  # noqa: E402


def _ja_tem_bpa_na_porta(porta: int) -> bool:
    """Alguém já está escutando nesta porta -- evita 2 instâncias brigando pelo
    socket (a tarefa agendada pode disparar de novo enquanto uma cópia anterior
    ainda está de pé; sem isso a 2ª quebra com WinError 10048 e conta como
    tentativa "falhada" da tarefa)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", porta)) == 0


if __name__ == "__main__":
    if _ja_tem_bpa_na_porta(PORTA):
        print(f"\n  BPA já está rodando em http://localhost:{PORTA} -- não abro outra cópia.\n")
    else:
        print(f"\n  BPA -> http://localhost:{PORTA}\n")
        uvicorn.run("bpa_local.main:app", host="127.0.0.1", port=PORTA, log_level="warning", use_colors=False)
