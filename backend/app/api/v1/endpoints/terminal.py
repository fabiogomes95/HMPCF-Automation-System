from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser

router = APIRouter()


class SessaoIn(BaseModel):
    terminal_nome: str
    ip_address: Optional[str] = ""


@router.post("/start")
async def iniciar_sessao(dados: SessaoIn, usuario: CurrentUser):
    return {"status": "ok", "terminal": dados.terminal_nome}


@router.post("/ping")
async def ping_sessao(terminal_nome: str, usuario: CurrentUser):
    return {"status": "ok"}
