from __future__ import annotations

from logging import getLogger
from typing import Optional

from app.database.legacy import get_legacy_conn
from app.repositories import paciente_repository as paciente_repo

logger = getLogger(__name__)


def criar_paciente(dados: dict) -> dict:
    conn = get_legacy_conn()
    try:
        return paciente_repo.inserir(conn, dados)
    finally:
        conn.close()


def atualizar_paciente(cpf: str, dados: dict) -> Optional[dict]:
    conn = get_legacy_conn()
    try:
        return paciente_repo.atualizar(conn, cpf, dados)
    finally:
        conn.close()


def deletar_paciente(cpf: str) -> bool:
    conn = get_legacy_conn()
    try:
        return paciente_repo.deletar(conn, cpf)
    finally:
        conn.close()


def contar_pacientes() -> int:
    conn = get_legacy_conn()
    try:
        return paciente_repo.contar(conn)
    finally:
        conn.close()
