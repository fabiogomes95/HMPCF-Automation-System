from typing import Optional
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_conn

router = APIRouter()


class SessaoIn(BaseModel):
    terminal_nome: str
    ip_address: Optional[str] = ""


@router.post("/start")
def iniciar_sessao(dados: SessaoIn):
    conn = get_conn()
    try:
        agora = datetime.now().isoformat(timespec="seconds")
        conn.execute("""
            INSERT INTO terminal_sessions (terminal_nome, ip_address, ultimo_ping)
            VALUES (?,?,?)
            ON CONFLICT(terminal_nome) DO UPDATE SET
                ip_address=excluded.ip_address,
                ultimo_ping=excluded.ultimo_ping
        """, (dados.terminal_nome, dados.ip_address, agora))
        conn.commit()
        return {"status": "ok", "terminal": dados.terminal_nome}
    finally:
        conn.close()


@router.post("/ping")
def ping_sessao(terminal_nome: str):
    conn = get_conn()
    try:
        agora = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE terminal_sessions SET ultimo_ping=? WHERE terminal_nome=?",
            (agora, terminal_nome),
        )
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
