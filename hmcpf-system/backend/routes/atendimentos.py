from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_conn

router = APIRouter()


class AtendimentoIn(BaseModel):
    paciente_id: int
    data_atendimento: Optional[str] = ""
    hora_atendimento: Optional[str] = ""
    registro: Optional[str] = ""
    procedencia: Optional[str] = ""


@router.post("")
def criar_atendimento(dados: AtendimentoIn):
    conn = get_conn()
    try:
        cur = conn.cursor()

        # Busca cpf/sus do paciente
        cur.execute("SELECT cpf, sus FROM pacientes WHERE rowid=?", (dados.paciente_id,))
        row = cur.fetchone()
        cpf = row["cpf"] if row else ""
        sus = row["sus"] if row else ""

        cur.execute("""
            INSERT INTO atendimentos
            (cpf, sus, data_atendimento, hora_atendimento,
             registro, procedencia, paciente_id)
            VALUES (?,?,?,?,?,?,?)
        """, (
            cpf, sus,
            dados.data_atendimento, dados.hora_atendimento,
            dados.registro, dados.procedencia,
            dados.paciente_id,
        ))
        conn.commit()
        return {"id": cur.lastrowid, "status": "sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
