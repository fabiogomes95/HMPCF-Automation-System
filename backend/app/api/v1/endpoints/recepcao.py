from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.recepcao import (
    PacienteAgrupadoResponse,
    RecepcaoCreate,
    RecepcaoListResponse,
    RecepcaoResponse,
    RecepcaoUpdate,
)
from app.services.recepcao_service import RecepcaoService

router = APIRouter()


def _svc(session: DBSession, usuario: Usuario) -> RecepcaoService:
    return RecepcaoService(session, usuario)


@router.get(
    "/",
    response_model=PaginatedResponse[RecepcaoListResponse],
    summary="Listar atendimentos (recentes primeiro, com busca opcional)",
)
async def listar_atendimentos(
    session: DBSession,
    usuario: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Busca por nome ou CPF do paciente"),
) -> PaginatedResponse[RecepcaoListResponse]:
    return await _svc(session, usuario).listar(page=page, page_size=page_size, q=q)


@router.get(
    "/pacientes/agrupado",
    response_model=PaginatedResponse[PacienteAgrupadoResponse],
    summary="Buscar pacientes únicos agrupados com total de entradas",
)
async def buscar_pacientes_agrupados(
    session: DBSession,
    usuario: CurrentUser,
    q: str = Query(..., min_length=3, description="Busca por nome, CPF ou CNS"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PacienteAgrupadoResponse]:
    return await _svc(session, usuario).listar_agrupado(page=page, page_size=page_size, q=q)


@router.get(
    "/recentes",
    response_model=PaginatedResponse[RecepcaoListResponse],
    summary="Últimos atendimentos registrados",
)
async def atendimentos_recentes(
    session: DBSession,
    usuario: CurrentUser,
    page_size: int = Query(10, ge=1, le=50),
) -> PaginatedResponse[RecepcaoListResponse]:
    return await _svc(session, usuario).listar_recentes(page=1, page_size=page_size)


@router.get(
    "/paciente/{paciente_id}",
    response_model=PaginatedResponse[RecepcaoListResponse],
    summary="Histórico de atendimentos de um paciente",
)
async def atendimentos_do_paciente(
    paciente_id: int,
    session: DBSession,
    usuario: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[RecepcaoListResponse]:
    return await _svc(session, usuario).listar_por_paciente(
        paciente_id=paciente_id, page=page, page_size=page_size
    )


@router.get(
    "/{atendimento_id}",
    response_model=RecepcaoResponse,
    summary="Detalhe completo da ficha de atendimento",
)
async def obter_atendimento(
    atendimento_id: int,
    session: DBSession,
    usuario: CurrentUser,
) -> RecepcaoResponse:
    return await _svc(session, usuario).obter(atendimento_id)


@router.post(
    "/",
    response_model=RecepcaoResponse,
    status_code=201,
    summary="Registrar novo atendimento",
)
async def criar_atendimento(
    data: RecepcaoCreate,
    session: DBSession,
    usuario: CurrentUser,
) -> RecepcaoResponse:
    return await _svc(session, usuario).criar(data)


@router.put(
    "/{atendimento_id}",
    response_model=RecepcaoResponse,
    summary="Atualizar ficha de atendimento",
)
async def atualizar_atendimento(
    atendimento_id: int,
    data: RecepcaoUpdate,
    session: DBSession,
    usuario: CurrentUser,
) -> RecepcaoResponse:
    return await _svc(session, usuario).atualizar(atendimento_id, data)


@router.delete(
    "/{atendimento_id}",
    status_code=204,
    summary="Remover atendimento",
)
async def remover_atendimento(
    atendimento_id: int,
    session: DBSession,
    usuario: CurrentUser,
) -> None:
    await _svc(session, usuario).remover(atendimento_id)
