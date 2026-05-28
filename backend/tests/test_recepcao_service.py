from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.repositories.recepcao_repository import RecepcaoRepository
from app.services.recepcao_service import RecepcaoService


@pytest.mark.asyncio
async def test_listar_agrupado(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    svc = RecepcaoService(session)

    for p in [paciente, paciente2]:
        for _ in range(3):
            atd = RecepcaoAtendimento(
                paciente_id=p.id,
                data_atendimento=datetime.now(timezone.utc),
            )
            session.add(atd)
    await session.flush()

    result = await svc.listar_agrupado(page=1, page_size=20, q="MARIA")
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].nome == "MARIA SILVA"
    assert result.items[0].total_entradas >= 3
    assert result.items[0].paciente_id == paciente.id


@pytest.mark.asyncio
async def test_listar_agrupado_sem_resultados(session: AsyncSession):
    svc = RecepcaoService(session)
    result = await svc.listar_agrupado(page=1, page_size=20, q="ZZZZZZ")
    assert result.total == 0
    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_listar_agrupado_sem_query(session: AsyncSession):
    svc = RecepcaoService(session)
    result = await svc.listar_agrupado(page=1, page_size=20, q=None)
    assert result.total == 0


@pytest.mark.asyncio
async def test_listar_por_paciente(session: AsyncSession, paciente: Paciente):
    svc = RecepcaoService(session)

    for _ in range(2):
        atd = RecepcaoAtendimento(
            paciente_id=paciente.id,
            data_atendimento=datetime.now(timezone.utc),
        )
        session.add(atd)
    await session.flush()

    result = await svc.listar_por_paciente(paciente.id, page=1, page_size=10)
    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_listar_por_paciente_not_found(session: AsyncSession):
    svc = RecepcaoService(session)
    with pytest.raises(NotFoundError):
        await svc.listar_por_paciente(99999, page=1, page_size=10)


@pytest.mark.asyncio
async def test_criar_atendimento(session: AsyncSession, paciente: Paciente):
    svc = RecepcaoService(session)
    from app.schemas.recepcao import RecepcaoCreate

    data = RecepcaoCreate(
        paciente_id=paciente.id,
        procedencia="SAMU",
    )
    result = await svc.criar(data)
    assert result.id is not None
    assert result.paciente_id == paciente.id
    assert result.procedencia == "SAMU"
    assert result.paciente is not None
    assert result.paciente.nome == "MARIA SILVA"
