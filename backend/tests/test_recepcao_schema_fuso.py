"""Hora sem fuso vinda da tela é sempre a do hospital (America/Sao_Paulo) --
não depende do timezone configurado no PostgreSQL."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.schemas.recepcao import RecepcaoCreate, RecepcaoUpdate

SP = ZoneInfo("America/Sao_Paulo")


def test_create_sem_fuso_vira_horario_de_brasilia():
    r = RecepcaoCreate(paciente_id=1, data_atendimento="2026-11-11T14:00:00")
    assert r.data_atendimento == datetime(2026, 11, 11, 14, 0, tzinfo=SP)
    assert r.data_atendimento.astimezone(timezone.utc).hour == 17


def test_update_sem_fuso_vira_horario_de_brasilia():
    r = RecepcaoUpdate(data_atendimento="2026-11-11T03:30:00")
    assert r.data_atendimento.astimezone(timezone.utc) == datetime(2026, 11, 11, 6, 30, tzinfo=timezone.utc)


def test_hora_com_fuso_explicito_nao_muda():
    r = RecepcaoCreate(paciente_id=1, data_atendimento="2026-11-11T14:00:00+00:00")
    assert r.data_atendimento == datetime(2026, 11, 11, 14, 0, tzinfo=timezone.utc)


def test_sem_data_continua_none():
    assert RecepcaoCreate(paciente_id=1).data_atendimento is None
    assert RecepcaoUpdate().data_atendimento is None
