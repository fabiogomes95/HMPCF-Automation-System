from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.repositories.recepcao_repository import RecepcaoRepository


@pytest.mark.asyncio
async def test_add_and_get_by_id(session: AsyncSession, paciente: Paciente):
    repo = RecepcaoRepository(session)
    atd = RecepcaoAtendimento(
        paciente_id=paciente.id,
        data_atendimento=datetime.now(timezone.utc),
        procedencia="NORMAL",
    )
    created = await repo.add_and_load(atd)
    assert created.id is not None

    found = await repo.get_by_id(created.id)
    assert found is not None
    assert found.paciente_id == paciente.id
    assert found.paciente is not None
    assert found.paciente.nome == "MARIA SILVA"


@pytest.mark.asyncio
async def test_list_recent(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    repo = RecepcaoRepository(session)

    for p in [paciente, paciente2]:
        atd = RecepcaoAtendimento(
            paciente_id=p.id,
            data_atendimento=datetime.now(timezone.utc),
        )
        session.add(atd)
    await session.flush()

    items = await repo.list_recent(limit=10, offset=0)
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_by_paciente(session: AsyncSession, paciente: Paciente):
    repo = RecepcaoRepository(session)

    for _ in range(3):
        atd = RecepcaoAtendimento(
            paciente_id=paciente.id,
            data_atendimento=datetime.now(timezone.utc),
        )
        session.add(atd)
    await session.flush()

    items = await repo.list_by_paciente(paciente.id, limit=10, offset=0)
    assert len(items) == 3


@pytest.mark.asyncio
async def test_count_by_paciente(session: AsyncSession, paciente: Paciente):
    repo = RecepcaoRepository(session)

    for _ in range(2):
        atd = RecepcaoAtendimento(
            paciente_id=paciente.id,
            data_atendimento=datetime.now(timezone.utc),
        )
        session.add(atd)
    await session.flush()

    count = await repo.count_by_paciente(paciente.id)
    assert count == 2


@pytest.mark.asyncio
async def test_list_by_query(session: AsyncSession, paciente: Paciente):
    repo = RecepcaoRepository(session)
    atd = RecepcaoAtendimento(
        paciente_id=paciente.id,
        data_atendimento=datetime.now(timezone.utc),
    )
    session.add(atd)
    await session.flush()

    items = await repo.list_by_query("MARIA", limit=10, offset=0)
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_search_grouped_by_patient(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    repo = RecepcaoRepository(session)

    for p in [paciente, paciente2]:
        for _ in range(2):
            atd = RecepcaoAtendimento(
                paciente_id=p.id,
                data_atendimento=datetime.now(timezone.utc),
            )
            session.add(atd)
    await session.flush()

    rows = await repo.search_grouped_by_patient("MARIA", limit=10, offset=0)
    assert len(rows) == 1
    assert rows[0].total_entradas == 2
    assert rows[0].nome == "MARIA SILVA"


@pytest.mark.asyncio
async def test_count_grouped_by_patient(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    repo = RecepcaoRepository(session)

    for p in [paciente, paciente2]:
        atd = RecepcaoAtendimento(
            paciente_id=p.id,
            data_atendimento=datetime.now(timezone.utc),
        )
        session.add(atd)
    await session.flush()

    count = await repo.count_grouped_by_patient("SILVA")
    assert count == 1

    count_all = await repo.count_grouped_by_patient("a")
    assert count_all == 2
