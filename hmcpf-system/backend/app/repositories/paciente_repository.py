from __future__ import annotations

import math
import sqlite3
from typing import Any, Optional


def listar(
    conn: sqlite3.Connection,
    nome: Optional[str] = None,
    cpf: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    cursor = conn.cursor()
    conditions: list[str] = []
    params: list[str] = []

    if cpf:
        conditions.append("cpf = ?")
        params.append(cpf)
    if nome:
        nome_sanitized = nome.replace("%", "\\%").replace("_", "\\_")
        conditions.append("nome LIKE ? ESCAPE '\\'")
        params.append(f"%{nome_sanitized}%")

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

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
        "items": [dict(r) for r in rows],
        "total": total,
        "pagina": pagina,
        "total_paginas": total_paginas,
        "por_pagina": por_pagina,
    }


def buscar_por_cpf(conn: sqlite3.Connection, cpf: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes WHERE cpf = ?", (cpf,))
    row = cursor.fetchone()
    return dict(row) if row else None


def buscar_duplicata(conn: sqlite3.Connection, nome: str, dn: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM pacientes WHERE nome = ? AND dn = ? LIMIT 1",
        (nome, dn),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def inserir(conn: sqlite3.Connection, dados: dict) -> Optional[dict]:
    cursor = conn.cursor()
    cols = ", ".join(dados.keys())
    placeholders = ", ".join("?" for _ in dados)
    cursor.execute(
        f"INSERT INTO pacientes ({cols}) VALUES ({placeholders})",
        list(dados.values()),
    )
    conn.commit()
    return buscar_por_cpf(conn, dados["cpf"])


def atualizar(conn: sqlite3.Connection, cpf: str, dados: dict) -> Optional[dict]:
    cursor = conn.cursor()
    sets = ", ".join(f"{k} = ?" for k in dados)
    cursor.execute(
        f"UPDATE pacientes SET {sets} WHERE cpf = ?",
        [*dados.values(), cpf],
    )
    conn.commit()
    return buscar_por_cpf(conn, cpf)


def deletar(conn: sqlite3.Connection, cpf: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pacientes WHERE cpf = ?", (cpf,))
    conn.commit()
    return cursor.rowcount > 0


def contar(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]


def buscar_por_termo(conn: sqlite3.Connection, termo: str) -> list[dict]:
    import re as _re
    if not termo or len(termo) < 2:
        return []
    termo = termo.upper().strip()
    cur = conn.cursor()
    doc = _re.sub(r"\D", "", termo)
    resultados: list[dict] = []

    if termo != doc:
        cur.execute(
            "SELECT cpf, sus, nome, dn FROM pacientes WHERE nome LIKE ? LIMIT 50",
            (f"%{termo}%",),
        )
        for row in cur.fetchall():
            resultados.append(dict(row))

    if len(doc) >= 3:
        if len(doc) in (11, 15):
            cur.execute(
                "SELECT cpf, sus, nome, dn FROM pacientes WHERE cpf = ? OR sus = ? LIMIT 1",
                (doc, doc),
            )
            row = cur.fetchone()
            if row:
                row_dict = dict(row)
                if row_dict not in resultados:
                    resultados.insert(0, row_dict)
        cur.execute(
            "SELECT cpf, sus, nome, dn FROM pacientes WHERE cpf LIKE ? OR sus LIKE ? LIMIT 50",
            (f"{doc}%", f"{doc}%"),
        )
        for row in cur.fetchall():
            row_dict = dict(row)
            if row_dict not in resultados:
                resultados.append(row_dict)

    return resultados


def buscar_por_sus(conn: sqlite3.Connection, sus: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT cpf, nome, dn, sexo FROM pacientes WHERE sus = ?", (sus,))
    row = cursor.fetchone()
    return dict(row) if row else None


def listar_cpf_sus(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT cpf, sus FROM pacientes")
    return [dict(row) for row in cursor.fetchall() if row]


def inserir_ou_substituir(conn: sqlite3.Connection, dados: dict) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO pacientes (cpf, sus, nome, dn, sexo, raca, endereco, numero, bairro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            dados["cpf"], dados["sus"], dados["nome"], dados["dn"],
            dados.get("sexo", " "), dados.get("raca", "PARDA"),
            dados.get("endereco", ""), dados.get("numero", ""), dados.get("bairro", ""),
        ),
    )


def atualizar_por_sus(conn: sqlite3.Connection, sus: str, updates: dict[str, str]) -> None:
    cursor = conn.cursor()
    sets = ", ".join(f"{k} = ?" for k in updates)
    cursor.execute(
        f"UPDATE pacientes SET {sets} WHERE sus = ?",
        [*updates.values(), sus],
    )


def listar_todos(conn: sqlite3.Connection, mes_ano: str = "") -> list[sqlite3.Row]:
    cursor = conn.cursor()
    query = "SELECT cpf, sus, nome, dn, sexo, endereco, numero, bairro, tel FROM pacientes"
    params: list[str] = []
    if mes_ano:
        query += " WHERE dn LIKE ?"
        params.append(f"%-{mes_ano[:2]}-%")
    cursor.execute(query, params)
    return cursor.fetchall()
