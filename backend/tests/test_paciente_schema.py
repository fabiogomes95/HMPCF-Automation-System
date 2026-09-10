import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.paciente import PacienteCreate
from app.services.paciente_service import PacienteService

DADOS_BASE = {"nome": "TESTE SEM DOCUMENTO", "sexo": "M", "dtnasc": "19900101"}


def test_criar_schema_sem_cpf_nem_cns_e_valido():
    """CPF/CNS agora são opcionais no schema -- sem_documento é decidido
    pelo PacienteService, não pelo cliente."""
    paciente = PacienteCreate(**DADOS_BASE)
    assert paciente.num_cpf is None
    assert paciente.cns is None


@pytest.mark.asyncio
async def test_criar_sem_cpf_marca_sem_documento_automaticamente(session: AsyncSession):
    svc = PacienteService(session)
    resultado = await svc.criar(PacienteCreate(**DADOS_BASE, cns="700000000000005"))
    assert resultado.sem_documento is True


@pytest.mark.asyncio
async def test_criar_com_cpf_nao_marca_sem_documento(session: AsyncSession):
    svc = PacienteService(session)
    resultado = await svc.criar(PacienteCreate(**DADOS_BASE, num_cpf="52998224725"))
    assert resultado.sem_documento is False
