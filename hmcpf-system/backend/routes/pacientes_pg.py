"""
GET /api/v2/pacientes  —  busca de pacientes no PostgreSQL.

Parâmetros de query:
  q        — busca livre (nome, CPF ou CNS, mínimo 3 chars)
  limit    — max resultados (padrão 20, máx 100)
  offset   — paginação (padrão 0)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor
from database_pg import get_pg_conn, release_pg_conn

router = APIRouter()


def _pg_row_to_dict(row: dict) -> dict:
    """Converte linha do PostgreSQL para formato compatível com o frontend."""
    return {
        "id":           row["id"],
        "num_cpf":      row["NUM_CPF"],
        "cns":          row["CNS"],
        "nome":         row["NOME"],
        "dtnasc":       row["DTNASC"],
        "sexo":         row["SEXO"],
        "raca":         row["RACA"],
        "maepcn":       row["MAEPCN"],
        "logpcn":       row["LOGPCN"],
        "numpcn":       row["NUMPCN"],
        "bairro_pcnte": row["BAIRRO_PCNTE"],
        "nmres":        row["NMRES"],
        "ddd_tel":      row["DDTEL_PCNTE"],
        "telefone":     row["TEL_PCNTE"],
        "nome_social":  row["nomeSocial"],
        "idade":        row["idade"],
        "civil":        row["civil"],
        "ocupacao":     row["ocupacao"],
        "responsavel":  row["responsavel"],
        "cidade":       row["cidade"],
        "estado":       row["estado"],
    }


@router.get("")
def listar_pacientes(
    q:      Optional[str] = Query(None, min_length=3, description="Busca por nome, CPF ou CNS"),
    limit:  int           = Query(20,  ge=1, le=100),
    offset: int           = Query(0,   ge=0),
):
    """Lista pacientes do PostgreSQL com busca e paginação."""
    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if q:
                termo = f"%{q.upper()}%"
                cur.execute(
                    """
                    SELECT *, COUNT(*) OVER() AS _total
                    FROM pacientes
                    WHERE UPPER("NOME") LIKE %s
                       OR "NUM_CPF" LIKE %s
                       OR "CNS"     LIKE %s
                    ORDER BY "NOME"
                    LIMIT %s OFFSET %s
                    """,
                    (termo, f"%{q}%", f"%{q}%", limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT *, COUNT(*) OVER() AS _total
                    FROM pacientes
                    ORDER BY id
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )

            rows = cur.fetchall()
            total = rows[0]["_total"] if rows else 0

        return {
            "total":     total,
            "limit":     limit,
            "offset":    offset,
            "pacientes": [_pg_row_to_dict(dict(r)) for r in rows],
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        release_pg_conn(conn)


@router.get("/busca")
def buscar_paciente(documento: str = Query(..., min_length=3)):
    """Busca paciente por CPF ou CNS exato. Retorna null se não encontrado."""
    doc = "".join(c for c in documento if c.isdigit())
    if not doc:
        return None

    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT * FROM pacientes WHERE "NUM_CPF"=%s OR "CNS"=%s LIMIT 1',
                (doc, doc),
            )
            row = cur.fetchone()
        if not row:
            return None
        return _pg_row_to_dict(dict(row))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        release_pg_conn(conn)
