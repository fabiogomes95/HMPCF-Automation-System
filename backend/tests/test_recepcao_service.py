from datetime import date, datetime, timezone

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
async def test_planilha_mensal_classifica_turno_e_dia_referencia(
    session: AsyncSession, paciente: Paciente, paciente2: Paciente
):
    svc = RecepcaoService(session)

    diurno = RecepcaoAtendimento(
        paciente_id=paciente.id,
        data_atendimento=datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc),
    )
    noturno_mesmo_dia = RecepcaoAtendimento(
        paciente_id=paciente.id,
        data_atendimento=datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc),
    )
    # 03h do dia 16 pertence ao plantao noturno que comecou no dia 15
    madrugada_noturno_anterior = RecepcaoAtendimento(
        paciente_id=paciente2.id,
        data_atendimento=datetime(2026, 9, 16, 3, 0, tzinfo=timezone.utc),
    )
    session.add_all([diurno, noturno_mesmo_dia, madrugada_noturno_anterior])
    await session.flush()

    result = await svc.planilha_mensal(ano=2026, mes=9)
    por_id = {item.atendimento_id: item for item in result.items}

    assert por_id[diurno.id].turno == "DIURNO"
    assert por_id[diurno.id].dia_referencia == date(2026, 9, 15)

    assert por_id[noturno_mesmo_dia.id].turno == "NOTURNO"
    assert por_id[noturno_mesmo_dia.id].dia_referencia == date(2026, 9, 15)

    assert por_id[madrugada_noturno_anterior.id].turno == "NOTURNO"
    assert por_id[madrugada_noturno_anterior.id].dia_referencia == date(2026, 9, 15)


@pytest.mark.asyncio
async def test_planilha_mensal_vira_mes_no_plantao_noturno(session: AsyncSession, paciente: Paciente):
    """01h do dia 01/10 pertence ao noturno do dia 30/09 -- deve aparecer no
    relatorio de SETEMBRO, não no de OUTUBRO."""
    svc = RecepcaoService(session)

    virada = RecepcaoAtendimento(
        paciente_id=paciente.id,
        data_atendimento=datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc),
    )
    session.add(virada)
    await session.flush()

    setembro = await svc.planilha_mensal(ano=2026, mes=9)
    outubro = await svc.planilha_mensal(ano=2026, mes=10)

    ids_setembro = {item.atendimento_id for item in setembro.items}
    ids_outubro = {item.atendimento_id for item in outubro.items}

    assert virada.id in ids_setembro
    assert virada.id not in ids_outubro

    item = next(i for i in setembro.items if i.atendimento_id == virada.id)
    assert item.turno == "NOTURNO"
    assert item.dia_referencia == date(2026, 9, 30)


@pytest.mark.asyncio
async def test_planilha_mensal_monta_endereco_e_campos_extra(session: AsyncSession):
    svc = RecepcaoService(session)

    paciente_endereco = Paciente(
        nome="JOSE ENDERECO TESTE",
        num_cpf="11122233344",
        cns="111111111111111",
        dtnasc="19800101",
        sexo="M",
        raca="01",
        cidade="EXTREMOZ",
        logpcn="R. DAS FLORES",
        numpcn="123",
        bairro_pcnte="CENTRO",
        ddtel_pcnte="84",
        tel_pcnte="999998888",
    )
    session.add(paciente_endereco)
    await session.flush()
    await session.refresh(paciente_endereco)

    atd = RecepcaoAtendimento(
        paciente_id=paciente_endereco.id,
        registro=42,
        procedencia="SAMU",
        data_atendimento=datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc),
    )
    session.add(atd)
    await session.flush()

    result = await svc.planilha_mensal(ano=2026, mes=9)
    item = next(i for i in result.items if i.atendimento_id == atd.id)

    assert item.registro == 42
    assert item.procedencia == "SAMU"
    assert item.endereco == "R. DAS FLORES, 123 - CENTRO"
    assert item.telefone == "84999998888"


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
