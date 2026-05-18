from __future__ import annotations

import math
import sqlite3
from typing import Optional


def _iso_col() -> str:
    return (
        "substr(a.data_atendimento, 7, 4) || '-' || "
        "substr(a.data_atendimento, 4, 2) || '-' || "
        "substr(a.data_atendimento, 1, 2)"
    )


def _br_to_iso(data_br: str) -> str:
    partes = data_br.split("/")
    if len(partes) == 3 and len(partes[2]) == 4:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return data_br


def listar(
    conn: sqlite3.Connection,
    cpf: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
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
        "items": [dict(r) for r in rows],
        "total": total,
        "pagina": pagina,
        "total_paginas": total_paginas,
        "por_pagina": por_pagina,
    }


def inserir(conn: sqlite3.Connection, dados: dict) -> dict:
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


def contar(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
