"""
LOGGING.PY — Sistema de logs do HMPCF.

POR QUE LOGGING É IMPORTANTE:
  - print() desaparece em produção (sem terminal)
  - logging grava em arquivo + terminal simultaneamente
  - logging tem níveis: DEBUG < INFO < WARNING < ERROR < CRITICAL
  - logging mostra data/hora/módulo/linha — essencial para debug

COMO USAR EM QUALQUER ARQUIVO:
  from logging_setup import logger
  logger.info("Processo iniciado")
  logger.error(f"Falha ao conectar: {e}")

NÃO USE print() EM CÓDIGO PROFISSIONAL — USE logging.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> None:
    """
    Configura o logging UMA vez na inicialização do app.

    1. Cria diretório de logs se não existir
    2. Define formato da mensagem (timestamp + nível + módulo + mensagem)
    3. Adiciona saída para terminal (stdout)
    4. Adiciona saída para arquivo (logs/hmpcf.log)
    5. Silencia bibliotecas muito verbosas (uvicorn, httpx)
    """
    log_dir: Path = settings.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # Formato profissional: "2026-05-16 22:10:30 | INFO     | config.py:42 | Servidor iniciado"
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Logger raiz — tudo que for logado no sistema passa por aqui
    root_logger = logging.getLogger()
    root_logger.setLevel(
        getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    )

    # Handler 1: terminal (útil para desenvolvimento)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Handler 2: arquivo (essencial em produção)
    file_handler = logging.FileHandler(
        filename=log_dir / "hmpcf.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Reduz ruído de bibliotecas terceiras
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
