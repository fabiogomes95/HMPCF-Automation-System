from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.atendimento import (
    AtendimentoCreate,
    AtendimentoResponse,
    AtendimentoUpdate,
)
from app.services.atendimento_service import AtendimentoService

router = APIRouter(prefix="/api/v1", tags=["atendimentos"])


def get_service(db: Session = Depends(get_session)) -> AtendimentoService:
    return AtendimentoService(
        AtendimentoRepository(db),
        PacienteRepository(db),
    )


@router.get("/atendimentos", response_model=list[AtendimentoResponse])
def listar(
    skip: int = 0,
    limit: int = 100,
    service: AtendimentoService = Depends(get_service),
):
    return service.listar(skip, limit)


@router.get("/atendimentos/{id}", response_model=AtendimentoResponse)
def buscar_por_id(
    id: int,
    service: AtendimentoService = Depends(get_service),
):
    return service.buscar_por_id(id)


@router.get(
    "/pacientes/{paciente_id}/atendimentos",
    response_model=list[AtendimentoResponse],
)
def listar_por_paciente(
    paciente_id: int,
    skip: int = 0,
    limit: int = 100,
    service: AtendimentoService = Depends(get_service),
):
    return service.listar_por_paciente(paciente_id, skip, limit)


@router.post("/atendimentos", response_model=AtendimentoResponse, status_code=201)
def criar(
    data: AtendimentoCreate,
    service: AtendimentoService = Depends(get_service),
):
    return service.criar(data)


@router.put("/atendimentos/{id}", response_model=AtendimentoResponse)
def atualizar(
    id: int,
    data: AtendimentoUpdate,
    service: AtendimentoService = Depends(get_service),
):
    return service.atualizar(id, data)


@router.delete("/atendimentos/{id}", status_code=204)
def deletar(
    id: int,
    service: AtendimentoService = Depends(get_service),
):
    service.deletar(id)
