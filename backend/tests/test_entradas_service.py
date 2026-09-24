"""Aba Entradas: busca no sistema e nas planilhas manuais."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.atendimento_planilha import AtendimentoPlanilha
from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.services.entradas_service import buscar

FUSO = ZoneInfo("America/Sao_Paulo")
CPF = "52998224725"


def _planilha(data, hora, nome, cpf=None, linha=1):
    from app.importacao.planilhas_recepcao import nome_busca
    return AtendimentoPlanilha(data=data, hora=hora, nome=nome, nome_busca=nome_busca(nome), cpf=cpf,
                               arquivo="PLANILHA RECEPÇÃO.xlsx", aba="MAIO 2022", linha=linha)


@pytest_asyncio.fixture
async def dados(session: AsyncSession):
    p = Paciente(nome="JOSÉ DA CONCEIÇÃO", num_cpf=CPF, dtnasc="19800101")
    session.add(p)
    await session.flush()
    # no sistema: 10/09/2026 08:00 (também está na planilha) e 15/09/2026
    for dt in (datetime(2026, 9, 10, 8, 0, tzinfo=FUSO), datetime(2026, 9, 15, 23, 50, tzinfo=FUSO)):
        session.add(RecepcaoAtendimento(paciente_id=p.id, data_atendimento=dt))
    session.add_all([
        _planilha(date(2026, 9, 10), time(8, 20), "JOSE DA CONCEICAO", CPF, 10),     # mesmo atendimento
        _planilha(date(2022, 5, 3), time(7, 30), "JOSE DA CONCEICAO", CPF, 20),
        _planilha(date(2021, 9, 1), time(9, 0), "JOSE DA CONCEICAO", None, 30),       # 2021: sem CPF
        _planilha(date(2023, 1, 5), time(9, 0), "MARIA DA SILVA", "11144477735", 40),
    ])
    await session.flush()


@pytest.mark.asyncio
async def test_por_cpf_nas_duas_fontes_junta_o_mesmo_dia(session, dados):
    r = await buscar(session, "529.982.247-25", "ambos")
    assert r["criterio"] == "cpf" and len(r["pessoas"]) == 1
    p = r["pessoas"][0]
    assert p["cpf"] == CPF and p["total"] == 4
    datas = [e["data"] for e in p["entradas"]]
    assert datas == ["2026-09-15", "2026-09-10", "2022-05-03", "2021-09-01"]  # mais recente primeiro
    dia10 = p["entradas"][1]
    assert sorted(dia10["fontes"]) == ["planilha", "sistema"]                # uma entrada só
    assert p["entradas"][3]["pelo_nome"] is True                             # linha sem CPF, achada pelo nome
    assert p["por_ano"] == {2026: 2, 2022: 1, 2021: 1}


@pytest.mark.asyncio
async def test_escolher_a_fonte(session, dados):
    so_sistema = (await buscar(session, CPF, "sistema"))["pessoas"][0]
    assert so_sistema["total"] == 2 and all(e["fontes"] == ["sistema"] for e in so_sistema["entradas"])
    so_planilha = (await buscar(session, CPF, "planilhas"))["pessoas"][0]
    assert so_planilha["total"] == 3 and all(e["fontes"] == ["planilha"] for e in so_planilha["entradas"])


@pytest.mark.asyncio
async def test_por_nome_sem_acento_e_por_partes(session, dados):
    r = await buscar(session, "jose conceicao", "ambos")
    assert [p["cpf"] for p in r["pessoas"]] == [CPF]
    r = await buscar(session, "maria silva", "planilhas")
    assert r["pessoas"][0]["cpf"] == "11144477735" and r["pessoas"][0]["total"] == 1


@pytest.mark.asyncio
async def test_busca_curta_demais(session):
    with pytest.raises(ValidationError):
        await buscar(session, "ab", "ambos")
