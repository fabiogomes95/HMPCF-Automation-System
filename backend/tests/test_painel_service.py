import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.services.painel_service import _cidade, montar_painel

FUSO = ZoneInfo("America/Sao_Paulo")


@pytest.mark.asyncio
async def test_painel_agrega_sem_dado_pessoal(session: AsyncSession, paciente: Paciente):
    paciente.bairro_pcnte = "CENTRO"
    paciente.cidade = "Natal-RN"
    agora = datetime.now(FUSO)
    # 2 atendimentos hoje do mesmo paciente (1 retorno) + 1 de 3 dias atrás
    for quando in (agora - timedelta(minutes=5), agora - timedelta(minutes=1), agora - timedelta(days=3)):
        session.add(RecepcaoAtendimento(paciente_id=paciente.id, data_atendimento=quando, procedencia="SAMU"))
    await session.flush()

    hoje = await montar_painel(session, "hoje")
    assert hoje["destaques"]["hoje"] == 2
    assert hoje["resumo"] == {"total": 2, "dias": 1, "media_dia": 2.0, "pacientes_unicos": 1, "retornos": 1}

    semana = await montar_painel(session, "7d")
    assert semana["resumo"]["total"] == 3
    assert len(semana["serie"]) == 7  # dias sem atendimento entram com zero
    assert sum(s["total"] for s in semana["serie"]) == 3
    assert semana["cidades"][0] == {"rotulo": "NATAL", "total": 3}
    assert semana["bairros"][0] == {"rotulo": "CENTRO", "total": 3}
    assert semana["procedencias"] == [{"rotulo": "SAMU", "total": 3}]
    assert sum(f["total"] for f in semana["faixas"]) == 3

    # Nada que identifique o paciente sai na resposta.
    texto = json.dumps(semana, ensure_ascii=False, default=str)
    for pessoal in (paciente.nome, paciente.num_cpf, paciente.cns, paciente.dtnasc):
        assert pessoal not in texto


def test_cidade_unifica_grafias():
    assert _cidade("Natal-RN") == "NATAL"
    assert _cidade("NATAL") == "NATAL"
    assert _cidade("São G. do Amarante") == "SAO GONCALO DO AMARANTE"
    assert _cidade("  ") == "Não informado"
