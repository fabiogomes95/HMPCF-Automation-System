import re
import sqlite3
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_conn

router = APIRouter()


def apenas_numeros(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k.lower(): row[k] for k in row.keys()}


class PacienteIn(BaseModel):
    num_cpf: Optional[str] = ""
    cns: Optional[str] = ""
    nome: Optional[str] = ""
    nome_social: Optional[str] = ""
    dtnasc: Optional[str] = ""
    sexo: Optional[str] = ""
    raca: Optional[str] = ""
    maepcn: Optional[str] = ""
    logpcn: Optional[str] = ""
    numpcn: Optional[str] = ""
    bairro_pcnte: Optional[str] = ""
    ceppcn: Optional[str] = ""
    ibge: Optional[str] = ""
    etnia: Optional[str] = ""
    nacionalidade: Optional[str] = ""
    idade: Optional[str] = ""
    estado_civil: Optional[str] = ""
    ocupacao: Optional[str] = ""
    responsavel: Optional[str] = ""
    telefone: Optional[str] = ""
    cidade: Optional[str] = ""
    estado: Optional[str] = ""


def _upsert(cur: sqlite3.Cursor, dados: PacienteIn) -> int:
    """Insere ou atualiza paciente. Retorna rowid."""
    cpf = apenas_numeros(dados.num_cpf)
    cns = apenas_numeros(dados.cns)

    # Tenta achar existente por CPF ou CNS
    rowid = None
    if cpf:
        cur.execute("SELECT rowid FROM pacientes WHERE NUM_CPF=?", (cpf,))
        row = cur.fetchone()
        if row:
            rowid = row[0]
    if rowid is None and cns:
        cur.execute("SELECT rowid FROM pacientes WHERE CNS=?", (cns,))
        row = cur.fetchone()
        if row:
            rowid = row[0]

    if rowid:
        cur.execute("""
            UPDATE pacientes SET
                CNS=?, NUM_CPF=?, NOME=?, NOME_SOCIAL=?, DTNASC=?,
                SEXO=?, RACA=?, MAEPCN=?, LOGPCN=?, NUMPCN=?,
                BAIRRO_PCNTE=?, CEPPCN=?, IBGE=?, ETNIA=?,
                NACIONALIDADE=?, IDADE=?, ESTADO_CIVIL=?,
                OCUPACAO=?, RESPONSAVEL=?, TELEFONE=?, CIDADE=?, ESTADO=?
            WHERE rowid=?
        """, (
            cns, cpf, dados.nome, dados.nome_social, dados.dtnasc,
            dados.sexo, dados.raca, dados.maepcn, dados.logpcn, dados.numpcn,
            dados.bairro_pcnte, dados.ceppcn, dados.ibge, dados.etnia,
            dados.nacionalidade, dados.idade, dados.estado_civil,
            dados.ocupacao, dados.responsavel, dados.telefone,
            dados.cidade, dados.estado, rowid,
        ))
    else:
        cur.execute("""
            INSERT INTO pacientes
            (CNS, NUM_CPF, NOME, NOME_SOCIAL, DTNASC,
             SEXO, RACA, MAEPCN, LOGPCN, NUMPCN,
             BAIRRO_PCNTE, CEPPCN, IBGE, ETNIA,
             NACIONALIDADE, IDADE, ESTADO_CIVIL,
             OCUPACAO, RESPONSAVEL, TELEFONE, CIDADE, ESTADO)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            cns, cpf, dados.nome, dados.nome_social, dados.dtnasc,
            dados.sexo, dados.raca, dados.maepcn, dados.logpcn, dados.numpcn,
            dados.bairro_pcnte, dados.ceppcn, dados.ibge, dados.etnia,
            dados.nacionalidade, dados.idade, dados.estado_civil,
            dados.ocupacao, dados.responsavel, dados.telefone,
            dados.cidade, dados.estado,
        ))
        rowid = cur.lastrowid

    return rowid


@router.get("/busca")
def buscar_paciente(documento: str):
    """Busca paciente por CPF ou CNS. Retorna null se não encontrado."""
    doc = apenas_numeros(documento)
    if not doc:
        return None
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT rowid, * FROM pacientes WHERE NUM_CPF=? OR CNS=?",
            (doc, doc),
        )
        row = cur.fetchone()
        if not row:
            return None
        d = row_to_dict(row)
        d["id"] = row["rowid"]
        return d
    finally:
        conn.close()


@router.post("")
def criar_paciente(dados: PacienteIn):
    conn = get_conn()
    try:
        cur = conn.cursor()
        rowid = _upsert(cur, dados)
        conn.commit()
        cur.execute("SELECT rowid, * FROM pacientes WHERE rowid=?", (rowid,))
        row = cur.fetchone()
        d = row_to_dict(row)
        d["id"] = rowid
        return d
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.put("/{paciente_id}")
def atualizar_paciente(paciente_id: int, dados: PacienteIn):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT rowid FROM pacientes WHERE rowid=?", (paciente_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Paciente não encontrado")
        cpf = apenas_numeros(dados.num_cpf)
        cns = apenas_numeros(dados.cns)
        cur.execute("""
            UPDATE pacientes SET
                CNS=?, NUM_CPF=?, NOME=?, NOME_SOCIAL=?, DTNASC=?,
                SEXO=?, RACA=?, MAEPCN=?, LOGPCN=?, NUMPCN=?,
                BAIRRO_PCNTE=?, CEPPCN=?, IBGE=?, ETNIA=?,
                NACIONALIDADE=?, IDADE=?, ESTADO_CIVIL=?,
                OCUPACAO=?, RESPONSAVEL=?, TELEFONE=?, CIDADE=?, ESTADO=?
            WHERE rowid=?
        """, (
            cns, cpf, dados.nome, dados.nome_social, dados.dtnasc,
            dados.sexo, dados.raca, dados.maepcn, dados.logpcn, dados.numpcn,
            dados.bairro_pcnte, dados.ceppcn, dados.ibge, dados.etnia,
            dados.nacionalidade, dados.idade, dados.estado_civil,
            dados.ocupacao, dados.responsavel, dados.telefone,
            dados.cidade, dados.estado, paciente_id,
        ))
        conn.commit()
        cur.execute("SELECT rowid, * FROM pacientes WHERE rowid=?", (paciente_id,))
        row = cur.fetchone()
        d = row_to_dict(row)
        d["id"] = paciente_id
        return d
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
