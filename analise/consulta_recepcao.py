"""
CONSULTA_RECEPCAO.PY — Consulta e estatísticas da recepção (hospital.db)
=======================================================================
Usado pelo app_painel.py para exibir no painel de gestão.
Lê diretamente do SQLite da recepção (hospital.db).
"""

import os
import sqlite3
from logging_setup import logger
from config import DB_SQLITE

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _db_path() -> str:
    path = DB_SQLITE
    if not os.path.isabs(path):
        path = os.path.join(SRC_DIR, path)
    return path


def _criar_indices(conn: sqlite3.Connection) -> None:
    try:
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_atendimentos_cpf
                ON atendimentos(cpf);
            CREATE INDEX IF NOT EXISTS idx_atendimentos_sus
                ON atendimentos(sus);
            CREATE INDEX IF NOT EXISTS idx_atendimentos_data
                ON atendimentos(data_atendimento);
        """)
    except Exception as e:
        logger.warning(f"Nao foi possivel criar indices: {e}")


def _conectar() -> sqlite3.Connection | None:
    path = _db_path()
    if not os.path.exists(path):
        logger.warning(f"hospital.db nao encontrado em: {path}")
        return None
    try:
        conn = sqlite3.connect(path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        _criar_indices(conn)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar hospital.db: {e}")
        return None


def consultar_atendimentos(data_inicio: str, data_fim: str) -> list[dict]:
    conn = _conectar()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                a.id, a.data_atendimento, a.hora_atendimento,
                a.registro, a.procedencia, a.cpf, a.sus,
                p.nome, p.dn, p.endereco, p.bairro, p.cidade, p.tel
            FROM atendimentos a
            LEFT JOIN pacientes p ON (p.cpf = a.cpf OR p.sus = a.sus)
            WHERE a.data_atendimento BETWEEN ? AND ?
            ORDER BY a.data_atendimento DESC, a.hora_atendimento DESC
        """, (data_inicio, data_fim))

        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        logger.info(f"Consulta retornou {len(rows)} linhas")
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao consultar atendimentos: {e}")
        return []
    finally:
        conn.close()


def resumo_atendimentos(data_inicio: str, data_fim: str) -> dict:
    conn = _conectar()
    if not conn:
        return {"total": 0, "por_procedencia": {}, "media_dia": 0}

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM atendimentos
            WHERE data_atendimento BETWEEN ? AND ?
        """, (data_inicio, data_fim))
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(procedencia, 'NORMAL') as proc, COUNT(*) as qtd
            FROM atendimentos
            WHERE data_atendimento BETWEEN ? AND ?
            GROUP BY proc ORDER BY qtd DESC
        """, (data_inicio, data_fim))
        por_procedencia = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT COUNT(DISTINCT data_atendimento) FROM atendimentos
            WHERE data_atendimento BETWEEN ? AND ?
        """, (data_inicio, data_fim))
        dias = cursor.fetchone()[0] or 1
        media_dia = round(total / dias, 1)

        return {
            "total": total,
            "por_procedencia": por_procedencia,
            "media_dia": media_dia,
        }
    except Exception as e:
        logger.error(f"Erro no resumo: {e}")
        return {"total": 0, "por_procedencia": {}, "media_dia": 0}
    finally:
        conn.close()


def atendimentos_por_dia(data_inicio: str, data_fim: str) -> list[dict]:
    conn = _conectar()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT data_atendimento, COUNT(*) as qtd
            FROM atendimentos
            WHERE data_atendimento BETWEEN ? AND ?
            GROUP BY data_atendimento
            ORDER BY data_atendimento
        """, (data_inicio, data_fim))
        return [{"data": row[0], "qtd": row[1]} for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Erro consulta por dia: {e}")
        return []
    finally:
        conn.close()
