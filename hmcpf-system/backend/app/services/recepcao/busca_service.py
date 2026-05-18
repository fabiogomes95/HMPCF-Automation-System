from __future__ import annotations

from logging import getLogger
from typing import Optional

from app.database.legacy import get_legacy_conn
from app.repositories import paciente_repository as paciente_repo

logger = getLogger(__name__)


def listar_pacientes(
    nome: Optional[str] = None,
    cpf: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    conn = get_legacy_conn()
    try:
        return paciente_repo.listar(conn, nome=nome, cpf=cpf, pagina=pagina, por_pagina=por_pagina)
    finally:
        conn.close()


def buscar_paciente(cpf: str) -> Optional[dict]:
    conn = get_legacy_conn()
    try:
        return paciente_repo.buscar_por_cpf(conn, cpf)
    finally:
        conn.close()


def buscar_duplicata(nome: str, dn: str) -> Optional[dict]:
    conn = get_legacy_conn()
    try:
        return paciente_repo.buscar_duplicata(conn, nome, dn)
    finally:
        conn.close()
