from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.paciente import (
    PacienteCreate,
    PacienteResponse,
    PacienteUpdate,
)
from app.services.paciente_service import PacienteService

router = APIRouter(prefix="/api/v1/pacientes", tags=["pacientes"])


def get_service(db: Session = Depends(get_session)) -> PacienteService:
    return PacienteService(PacienteRepository(db))


@router.get("", response_model=list[PacienteResponse])
def listar(
    skip: int = 0,
    limit: int = 100,
    service: PacienteService = Depends(get_service),
):
    return service.listar(skip, limit)


@router.get("/busca", response_model=PacienteResponse | None)
def buscar_por_documento(
    documento: str,
    service: PacienteService = Depends(get_service),
):
    return service.buscar_por_documento(documento)


@router.get("/{id}", response_model=PacienteResponse)
def buscar_por_id(
    id: int,
    service: PacienteService = Depends(get_service),
):
    return service.buscar_por_id(id)


@router.post("", response_model=PacienteResponse, status_code=201)
def criar(
    data: PacienteCreate,
    service: PacienteService = Depends(get_service),
):
    return service.criar(data)


@router.put("/{id}", response_model=PacienteResponse)
def atualizar(
    id: int,
    data: PacienteUpdate,
    service: PacienteService = Depends(get_service),
):
    return service.atualizar(id, data)


@router.delete("/{id}", status_code=204)
def deletar(
    id: int,
    service: PacienteService = Depends(get_service),
):
    service.deletar(id)
