from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate
from app.services.paciente_service import PacienteService

router = APIRouter()


def _svc(session: DBSession) -> PacienteService:
    return PacienteService(session)


@router.get("/", response_model=PaginatedResponse[PacienteResponse])
async def listar_pacientes(
    session: DBSession,
    usuario: CurrentUser,
    q: Optional[str] = Query(None, min_length=3, description="Busca por nome, CPF ou CNS"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PacienteResponse]:
    return await _svc(session).listar(q=q, page=page, page_size=page_size)


@router.get("/busca", response_model=PacienteResponse)
async def buscar_por_documento(
    session: DBSession,
    usuario: CurrentUser,
    documento: str = Query(..., min_length=3, description="CPF ou CNS do paciente"),
) -> PacienteResponse:
    return await _svc(session).buscar_por_documento(documento)


@router.get("/{paciente_id}", response_model=PacienteResponse)
async def obter_paciente(
    paciente_id: int,
    session: DBSession,
    usuario: CurrentUser,
) -> PacienteResponse:
    return await _svc(session).obter(paciente_id)


@router.post("/", response_model=PacienteResponse, status_code=201)
async def criar_paciente(
    data: PacienteCreate,
    session: DBSession,
    usuario: CurrentUser,
) -> PacienteResponse:
    return await _svc(session).criar(data)


@router.put("/{paciente_id}", response_model=PacienteResponse)
async def atualizar_paciente(
    paciente_id: int,
    data: PacienteUpdate,
    session: DBSession,
    usuario: CurrentUser,
) -> PacienteResponse:
    return await _svc(session).atualizar(paciente_id, data)


@router.delete("/{paciente_id}", status_code=204)
async def remover_paciente(
    paciente_id: int,
    session: DBSession,
    usuario: CurrentUser,
) -> None:
    await _svc(session).remover(paciente_id)
