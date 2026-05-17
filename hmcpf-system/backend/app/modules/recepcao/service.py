"""
SERVICE.PY — Lógica de negócio do módulo de recepção.

CONEXÃO COM O BANCO LEGADO:
  Este serviço conecta diretamente no hospital.db existente
  (sistema legado) usando sqlite3 puro.

  Futuramente, quando a migração estiver completa, os dados
  serão gerenciados pelo SQLAlchemy (models/). Por enquanto
  mantemos compatibilidade com o banco em produção.

FUNÇÕES:
  listar_pacientes     → GET    /pacientes?nome=&cpf=&pagina=
  buscar_paciente      → GET    /pacientes/{cpf}
  criar_paciente       → POST   /pacientes
  atualizar_paciente   → PUT    /pacientes/{cpf}
  deletar_paciente     → DELETE /pacientes/{cpf}
  listar_atendimentos  → GET    /pacientes/{cpf}/atendimentos
"""

from __future__ import annotations

import math
import os
import sqlite3
from logging import getLogger
from typing import Any, Optional

from app.core.config import settings

logger = getLogger(__name__)


def _db_path() -> str:
    """
    Retorna o caminho absoluto para o hospital.db.

    Prioridade:
      1. LEGACY_DB_PATH do .env (caminho explícito)
      2. ../hospital.db (relativo ao backend/)
      3. Raiz do projeto HMPCF legado
    """
    if settings.LEGACY_DB_PATH:
        return settings.LEGACY_DB_PATH

    # Sobe um nível: backend/ → hmcpf-system/ → HMPCF/
    base = settings.PROJECT_ROOT.parent
    candidates = [
        base / "hospital.db",
        settings.PROJECT_ROOT.parent / "hospital.db",
    ]
    for path in candidates:
        if path.exists():
            return str(path)

    # Fallback: ../hospital.db relativo ao backend/
    return str(settings.BASE_DIR.parent / "hospital.db")


def _get_conn() -> sqlite3.Connection:
    """Abre conexão com o hospital.db."""
    path = _db_path()
    if not os.path.exists(path):
        logger.warning("hospital.db nao encontrado em: %s", path)
        raise FileNotFoundError(f"hospital.db nao encontrado: {path}")
    conn = sqlite3.connect(path, timeout=settings.SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Converte sqlite3.Row para dicionário."""
    return dict(row) if row else {}


def _br_to_iso(data_br: str) -> str:
    """Converte DD/MM/AAAA para AAAA-MM-DD. Se não conseguir, retorna original."""
    partes = data_br.split("/")
    if len(partes) == 3 and len(partes[2]) == 4:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return data_br


def _iso_col() -> str:
    """Expressão SQL que converte data_atendimento (DD/MM/AAAA) para AAAA-MM-DD."""
    return (
        "substr(a.data_atendimento, 7, 4) || '-' || "
        "substr(a.data_atendimento, 4, 2) || '-' || "
        "substr(a.data_atendimento, 1, 2)"
    )


# ── PACIENTES ─────────────────────────────────────────────────


def listar_pacientes(
    nome: Optional[str] = None,
    cpf: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    """
    Lista pacientes com filtro opcional por nome ou CPF.

    A busca por nome usa LIKE com ESCAPE para evitar
    SQL injection (mesma proteção do sistema legado).
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        conditions: list[str] = []
        params: list[str] = []

        if cpf:
            conditions.append("cpf = ?")
            params.append(cpf)
        if nome:
            # Proteção contra LIKE injection
            nome_sanitized = nome.replace("%", "\\%").replace("_", "\\_")
            conditions.append("nome LIKE ? ESCAPE '\\'")
            params.append(f"%{nome_sanitized}%")

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        # Total para paginação
        cursor.execute(f"SELECT COUNT(*) FROM pacientes{where}", params)
        total = cursor.fetchone()[0]

        total_paginas = max(1, math.ceil(total / por_pagina))
        pagina = max(1, min(pagina, total_paginas))
        offset = (pagina - 1) * por_pagina

        cursor.execute(
            f"SELECT * FROM pacientes{where} ORDER BY nome LIMIT ? OFFSET ?",
            [*params, por_pagina, offset],
        )
        rows = cursor.fetchall()

        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "pagina": pagina,
            "total_paginas": total_paginas,
            "por_pagina": por_pagina,
        }
    finally:
        conn.close()


def buscar_paciente(cpf: str) -> Optional[dict]:
    """Busca um paciente pelo CPF."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pacientes WHERE cpf = ?", (cpf,))
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def buscar_duplicata(nome: str, dn: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pacientes WHERE nome = ? AND dn = ? LIMIT 1",
            (nome, dn),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def criar_paciente(dados: dict) -> dict:
    """Insere um novo paciente no banco legado."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cols = ", ".join(dados.keys())
        placeholders = ", ".join("?" for _ in dados)
        cursor.execute(
            f"INSERT INTO pacientes ({cols}) VALUES ({placeholders})",
            list(dados.values()),
        )
        conn.commit()
        return buscar_paciente(dados["cpf"])  # type: ignore
    finally:
        conn.close()


def atualizar_paciente(cpf: str, dados: dict) -> Optional[dict]:
    """Atualiza dados de um paciente existente."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        sets = ", ".join(f"{k} = ?" for k in dados)
        cursor.execute(
            f"UPDATE pacientes SET {sets} WHERE cpf = ?",
            [*dados.values(), cpf],
        )
        conn.commit()
        return buscar_paciente(cpf)
    finally:
        conn.close()


def deletar_paciente(cpf: str) -> bool:
    """Remove um paciente pelo CPF. Retorna True se removeu."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pacientes WHERE cpf = ?", (cpf,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def contar_pacientes() -> int:
    """Total de pacientes cadastrados."""
    conn = _get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    finally:
        conn.close()


# ── ATENDIMENTOS ──────────────────────────────────────────────


def listar_atendimentos(
    cpf: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    """
    Lista atendimentos com filtros opcionais.

    Se data_inicio e data_fim forem fornecidos, filtra pelo período.
    Se cpf for fornecido, filtra pelo paciente.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        conditions: list[str] = []
        params: list[str] = []

        if cpf:
            conditions.append("a.cpf = ?")
            params.append(cpf)
        if data_inicio:
            conditions.append(f"{_iso_col()} >= ?")
            params.append(_br_to_iso(data_inicio))
        if data_fim:
            conditions.append(f"{_iso_col()} <= ?")
            params.append(_br_to_iso(data_fim))

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT COUNT(*) FROM atendimentos a{where}
        """, params)
        total = cursor.fetchone()[0]

        total_paginas = max(1, math.ceil(total / por_pagina))
        pagina = max(1, min(pagina, total_paginas))
        offset = (pagina - 1) * por_pagina

        cursor.execute(f"""
            SELECT a.*, p.nome, p.dn, p.tel, p.endereco, p.bairro, p.cidade
            FROM atendimentos a
            LEFT JOIN pacientes p ON a.cpf = p.cpf
            {where}
            ORDER BY a.data_atendimento DESC, a.hora_atendimento DESC
            LIMIT ? OFFSET ?
        """, [*params, por_pagina, offset])
        rows = cursor.fetchall()

        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "pagina": pagina,
            "total_paginas": total_paginas,
            "por_pagina": por_pagina,
        }
    finally:
        conn.close()


def criar_atendimento(dados: dict) -> dict:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cols = ", ".join(dados.keys())
        ph = ", ".join("?" for _ in dados)
        cursor.execute(
            f"INSERT INTO atendimentos ({cols}) VALUES ({ph})",
            list(dados.values()),
        )
        conn.commit()
        return dict(cursor.execute(
            "SELECT * FROM atendimentos WHERE id = ?", (cursor.lastrowid,)
        ).fetchone())
    finally:
        conn.close()


def contar_atendimentos() -> int:
    """Total de atendimentos registrados."""
    conn = _get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
    finally:
        conn.close()
