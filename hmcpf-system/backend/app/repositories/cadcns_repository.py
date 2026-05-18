from __future__ import annotations

from logging import getLogger
from typing import Any

logger = getLogger(__name__)


def listar_pacientes(con: Any) -> list[tuple]:
    cur = con.cursor()
    cur.execute("""
        SELECT NOME, DTNASC, NUM_CPF, CNS, SEXO,
               LOGPCN, NUMPCN, BAIRRO_PCNTE, DDTEL_PCNTE, TEL_PCNTE
        FROM CADCNS
    """)
    return cur.fetchall()


def atualizar_paciente(con: Any, nome_limpo: str, cpf: str, sus: str, sexo: str,
                       rua: str, numero: str, bairro: str, ddd: str, tel: str,
                       nome_original: str, dtnasc: str) -> None:
    cur = con.cursor()
    cur.execute("""
        UPDATE CADCNS SET
            NOME = ?, NUM_CPF = ?, CNS = ?, SEXO = ?,
            LOGPCN = ?, NUMPCN = ?, BAIRRO_PCNTE = ?,
            DDTEL_PCNTE = ?, TEL_PCNTE = ?, CO_LOGRAD = ?
        WHERE NOME = ? AND DTNASC = ?
    """, (
        nome_limpo, cpf, sus, sexo,
        rua, numero, bairro, ddd, tel, "081",
        nome_original, dtnasc,
    ))


def listar_metadados_colunas(con: Any) -> list[tuple[str, str]]:
    cur = con.cursor()
    TEXT_TYPES = {14, 37, 40}
    NUM_TYPES = {7, 8, 10, 16, 27}
    cur.execute("""
        SELECT RF.RDB$FIELD_NAME, F.RDB$FIELD_TYPE
        FROM RDB$RELATION_FIELDS RF
        JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
        WHERE RF.RDB$RELATION_NAME = 'CADCNS'
    """)
    updates: list[tuple[str, str]] = []
    for col, tipo in cur.fetchall():
        col_nome = col.strip() if col else ""
        if not col_nome or col_nome.startswith("RDB$"):
            continue
        if tipo in TEXT_TYPES:
            updates.append((col_nome, "texto"))
        elif tipo in NUM_TYPES:
            updates.append((col_nome, "numero"))
    return updates


def corrigir_null_coluna(con: Any, coluna: str, kind: str) -> None:
    cur = con.cursor()
    valor = "" if kind == "texto" else 0
    cur.execute(f"UPDATE CADCNS SET {coluna} = ? WHERE {coluna} IS NULL", [valor])


def listar_duplicatas(con: Any) -> list[dict]:
    cur = con.cursor()
    cur.execute("SELECT RDB$DB_KEY, CNS, NUM_CPF, LOGPCN, TEL_PCNTE FROM CADCNS WHERE CNS IS NOT NULL ORDER BY CNS")
    registros: list[dict] = []
    for row in cur.fetchall():
        registros.append({
            "db_key": row[0].hex() if isinstance(row[0], bytes) else str(row[0]),
            "cns": str(row[1] or "").strip(),
            "cpf": str(row[2] or "").strip(),
            "endereco": str(row[3] or "").strip(),
            "tel": str(row[4] or "").strip(),
        })
    return registros


def deletar_por_db_key(con: Any, db_key: str) -> None:
    cur = con.cursor()
    cur.execute("DELETE FROM CADCNS WHERE RDB$DB_KEY = ?", [bytes.fromhex(db_key) if db_key else ""])


def buscar_por_documento(con: Any, documento: str) -> dict | None:
    if len(documento) == 15:
        campo = "CNS"
    elif len(documento) == 11:
        campo = "NUM_CPF"
    else:
        return None
    sql = f"""
        SELECT FIRST 1
            CNS, NUM_CPF, NOME, DTNASC, SEXO, RACA
        FROM CADCNS
        WHERE {campo} = ?
          AND NOME   IS NOT NULL AND TRIM(NOME)   <> ''
          AND DTNASC IS NOT NULL
          AND SEXO   IS NOT NULL AND TRIM(SEXO)   <> ''
          AND RACA   IS NOT NULL AND TRIM(RACA)   <> ''
    """
    cur = con.cursor()
    cur.execute(sql, (documento,))
    row = cur.fetchone()
    if not row:
        return None
    return {
        'cns':        row[0],
        'cpf':        row[1],
        'nome':       row[2],
        'nascimento': row[3],
        'sexo':       row[4],
        'raca':       row[5],
        'documento':  documento,
    }
