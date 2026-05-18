from __future__ import annotations

from logging import getLogger
from typing import Optional

from app.database.legacy import get_legacy_conn
from app.repositories import atendimento_repository as atendimento_repo

logger = getLogger(__name__)


def listar_atendimentos(
    cpf: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    conn = get_legacy_conn()
    try:
        return atendimento_repo.listar(conn, cpf=cpf, data_inicio=data_inicio, data_fim=data_fim, pagina=pagina, por_pagina=por_pagina)
    finally:
        conn.close()


def criar_atendimento(dados: dict) -> dict:
    conn = get_legacy_conn()
    try:
        return atendimento_repo.inserir(conn, dados)
    finally:
        conn.close()


def contar_atendimentos() -> int:
    conn = get_legacy_conn()
    try:
        return atendimento_repo.contar(conn)
    finally:
        conn.close()
