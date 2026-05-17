"""
AUDITORIA_LOG.PY — Log de auditoria do painel de gestão
=========================================================
Registra ações importantes num arquivo JSON Lines (auditoria.log).
Cada linha é um JSON com: timestamp, acao, detalhes, origem.
"""

import os
import json
from datetime import datetime
from logging_setup import logger

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(SRC_DIR, "auditoria.log")


def registrar(acao: str, detalhes: str = "", origem: str = "painel", tipo: str = "sistema") -> None:
    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "acao": acao,
            "detalhes": detalhes,
            "origem": origem,
            "tipo": tipo,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Erro ao registrar auditoria: {e}")


def listar(limite: int = 100, tipo: str | None = None) -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []

    entradas = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        e = json.loads(linha)
                        if tipo is None or e.get("tipo", "sistema") == tipo:
                            entradas.append(e)
                    except json.JSONDecodeError:
                        continue

        entradas.reverse()
        return entradas[:limite]
    except Exception as e:
        logger.error(f"Erro ao ler auditoria.log: {e}")
        return []
