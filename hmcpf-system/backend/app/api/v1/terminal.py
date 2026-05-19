from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.repositories.terminal_session_repository import (
    TerminalSessionRepository,
)
from app.schemas.terminal_session import (
    TerminalSessionCreate,
    TerminalSessionResponse,
)
from app.services.terminal_session_service import TerminalSessionService

router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])


def get_service(db: Session = Depends(get_session)) -> TerminalSessionService:
    return TerminalSessionService(TerminalSessionRepository(db))


@router.post("/start")
def iniciar_sessao(
    data: TerminalSessionCreate,
    service: TerminalSessionService = Depends(get_service),
):
    return service.iniciar(data)


@router.post("/ping")
def ping(
    terminal_nome: str,
    service: TerminalSessionService = Depends(get_service),
):
    return service.ping(terminal_nome)


@router.get("/{nome}", response_model=TerminalSessionResponse | None)
def buscar_terminal(
    nome: str,
    service: TerminalSessionService = Depends(get_service),
):
    return service.buscar(nome)
