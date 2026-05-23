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


# Mapeamento: campo do frontend → coluna no banco
_FRONT_TO_DB = {
    "num_cpf":      "cpf",
    "cns":          "sus",
    "nome":         "nome",
    "nome_social":  "nomeSocial",
    "dtnasc":       "dn",
    "sexo":         "sexo",
    "raca":         "raca",
    "maepcn":       "mae",
    "logpcn":       "endereco",
    "numpcn":       "numero",
    "bairro_pcnte": "bairro",
    "cidade":       "cidade",
    "estado":       "estado",
    "telefone":     "tel",
    "nacionalidade":"naturalidade",
    "estado_civil": "civil",
    "ocupacao":     "ocupacao",
    "responsavel":  "responsavel",
    "idade":        "idade",
}

# Mapeamento inverso: coluna no banco → campo do frontend
_DB_TO_FRONT = {v: k for k, v in _FRONT_TO_DB.items()}


def row_to_front(row: sqlite3.Row, rowid: int) -> dict:
    """Converte uma linha do banco para o formato esperado pelo frontend."""
    d = {"id": rowid}
    for db_col in row.keys():
        front_key = _DB_TO_FRONT.get(db_col, db_col)
        d[front_key] = row[db_col]
    return d


class PacienteIn(BaseModel):
    num_cpf:      Optional[str] = ""
    cns:          Optional[str] = ""
    nome:         Optional[str] = ""
    nome_social:  Optional[str] = ""
    dtnasc:       Optional[str] = ""
    sexo:         Optional[str] = ""
    raca:         Optional[str] = ""
    maepcn:       Optional[str] = ""
    logpcn:       Optional[str] = ""
    numpcn:       Optional[str] = ""
    bairro_pcnte: Optional[str] = ""
    ceppcn:       Optional[str] = ""
    cidade:       Optional[str] = ""
    estado:       Optional[str] = ""
    telefone:     Optional[str] = ""
    nacionalidade:Optional[str] = ""
    estado_civil: Optional[str] = ""
    ocupacao:     Optional[str] = ""
    responsavel:  Optional[str] = ""
    idade:        Optional[str] = ""
    ibge:         Optional[str] = ""
    etnia:        Optional[str] = ""


def _paciente_para_db(dados: PacienteIn) -> dict:
    """Converte o model do frontend para dict com colunas do banco."""
    cpf = apenas_numeros(dados.num_cpf)
    return {
        "cpf":          cpf,
        "sus":          apenas_numeros(dados.cns),
        "nome":         dados.nome or "",
        "nomeSocial":   dados.nome_social or "",
        "dn":           dados.dtnasc or "",
        "sexo":         dados.sexo or "",
        "raca":         dados.raca or "",
        "mae":          dados.maepcn or "",
        "endereco":     dados.logpcn or "",
        "numero":       dados.numpcn or "",
        "bairro":       dados.bairro_pcnte or "",
        "cidade":       dados.cidade or "",
        "estado":       dados.estado or "",
        "tel":          apenas_numeros(dados.telefone),
        "naturalidade": dados.nacionalidade or "",
        "civil":        dados.estado_civil or "",
        "ocupacao":     dados.ocupacao or "",
        "responsavel":  dados.responsavel or "",
        "idade":        dados.idade or "",
    }


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
            "SELECT rowid, * FROM pacientes WHERE cpf=? OR sus=?",
            (doc, doc),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row_to_front(row, row["rowid"])
    finally:
        conn.close()


@router.post("")
def criar_paciente(dados: PacienteIn):
    conn = get_conn()
    try:
        cur = conn.cursor()
        db = _paciente_para_db(dados)

        # Verifica se já existe por CPF ou SUS
        cpf = db["cpf"]
        sus = db["sus"]
        rowid = None
        if cpf:
            cur.execute("SELECT rowid FROM pacientes WHERE cpf=?", (cpf,))
            r = cur.fetchone()
            if r:
                rowid = r[0]
        if rowid is None and sus:
            cur.execute("SELECT rowid FROM pacientes WHERE sus=?", (sus,))
            r = cur.fetchone()
            if r:
                rowid = r[0]

        if rowid:
            # Atualiza existente
            sets = ", ".join(f"{k}=?" for k in db if k != "cpf")
            vals = [db[k] for k in db if k != "cpf"] + [rowid]
            cur.execute(f"UPDATE pacientes SET {sets} WHERE rowid=?", vals)
        else:
            cols = ", ".join(db.keys())
            placeholders = ", ".join("?" * len(db))
            cur.execute(
                f"INSERT INTO pacientes ({cols}) VALUES ({placeholders})",
                list(db.values()),
            )
            rowid = cur.lastrowid

        conn.commit()
        cur.execute("SELECT rowid, * FROM pacientes WHERE rowid=?", (rowid,))
        row = cur.fetchone()
        return row_to_front(row, rowid)
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

        db = _paciente_para_db(dados)
        sets = ", ".join(f"{k}=?" for k in db if k != "cpf")
        vals = [db[k] for k in db if k != "cpf"] + [paciente_id]
        cur.execute(f"UPDATE pacientes SET {sets} WHERE rowid=?", vals)
        conn.commit()

        cur.execute("SELECT rowid, * FROM pacientes WHERE rowid=?", (paciente_id,))
        row = cur.fetchone()
        return row_to_front(row, paciente_id)
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
