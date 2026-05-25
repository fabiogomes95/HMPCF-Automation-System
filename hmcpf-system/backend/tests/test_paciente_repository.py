import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.repositories.paciente_repository import PacienteRepository


@pytest.mark.asyncio
async def test_get_by_cpf(session: AsyncSession, paciente: Paciente):
    repo = PacienteRepository(session)
    found = await repo.get_by_cpf("12345678901")
    assert found is not None
    assert found.id == paciente.id
    assert found.nome == "MARIA SILVA"


@pytest.mark.asyncio
async def test_get_by_cpf_not_found(session: AsyncSession):
    repo = PacienteRepository(session)
    found = await repo.get_by_cpf("00000000000")
    assert found is None


@pytest.mark.asyncio
async def test_get_by_cns(session: AsyncSession, paciente: Paciente):
    repo = PacienteRepository(session)
    found = await repo.get_by_cns("123456789012345")
    assert found is not None
    assert found.id == paciente.id


@pytest.mark.asyncio
async def test_get_by_documento_cpf(session: AsyncSession, paciente: Paciente):
    repo = PacienteRepository(session)
    found = await repo.get_by_documento("12345678901")
    assert found is not None
    assert found.id == paciente.id


@pytest.mark.asyncio
async def test_get_by_documento_cns(session: AsyncSession, paciente: Paciente):
    repo = PacienteRepository(session)
    found = await repo.get_by_documento("123456789012345")
    assert found is not None
    assert found.id == paciente.id


@pytest.mark.asyncio
async def test_search_by_nome(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    repo = PacienteRepository(session)
    results = await repo.search("MARIA", limit=10, offset=0)
    assert len(results) == 1
    assert results[0].id == paciente.id


@pytest.mark.asyncio
async def test_search_by_cpf(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    repo = PacienteRepository(session)
    results = await repo.search("98765432100", limit=10, offset=0)
    assert len(results) == 1
    assert results[0].id == paciente2.id


@pytest.mark.asyncio
async def test_count_search(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    repo = PacienteRepository(session)
    count = await repo.count_search("SANTOS")
    assert count == 1

    count_all = await repo.count_search("a")
    assert count_all == 2
