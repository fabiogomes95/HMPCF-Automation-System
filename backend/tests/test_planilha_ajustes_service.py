"""Ajustes manuais da planilha (ordem/hora) — arquivo JSON, fora do banco."""
from datetime import date, timedelta

import pytest

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.services import planilha_ajustes_service as svc


@pytest.fixture(autouse=True)
def arquivo_temp(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PLANILHA_AJUSTES_FILE", str(tmp_path / "ajustes.json"))


def test_salva_e_le_do_mes():
    hoje = date.today()
    svc.salvar(hoje, "DIURNO", [3, 1, 2], {"1": "08:15"})
    ajustes = svc.do_mes(hoje.year, hoje.month)
    assert ajustes == {f"{hoje.isoformat()}|DIURNO": {"ordem": [3, 1, 2], "horas": {"1": "08:15"}}}


def test_vazio_volta_ao_automatico():
    hoje = date.today()
    svc.salvar(hoje, "NOTURNO", [2, 1], {})
    svc.salvar(hoje, "NOTURNO", [], {})
    assert svc.do_mes(hoje.year, hoje.month) == {}


def test_hora_invalida():
    with pytest.raises(ValidationError):
        svc.salvar(date.today(), "DIURNO", [], {"1": "25:00"})


def test_descarta_plantoes_antigos():
    velho = date.today() - timedelta(days=svc.DIAS_GUARDADOS + 5)
    svc.salvar(velho, "DIURNO", [1], {})
    svc.salvar(date.today(), "DIURNO", [2], {})
    assert svc.do_mes(velho.year, velho.month) == {}
