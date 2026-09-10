import pytest
from pydantic import ValidationError

from app.schemas.paciente import PacienteCreate

DADOS_BASE = {"nome": "TESTE SEM DOCUMENTO", "sexo": "M", "dtnasc": "19900101"}


def test_criar_sem_cpf_cns_e_sem_marcar_sem_documento_falha():
    with pytest.raises(ValidationError):
        PacienteCreate(**DADOS_BASE)


def test_criar_sem_cpf_cns_marcando_sem_documento_funciona():
    paciente = PacienteCreate(**DADOS_BASE, sem_documento=True)
    assert paciente.sem_documento is True
    assert paciente.num_cpf is None
    assert paciente.cns is None


def test_criar_com_cpf_valido_nao_precisa_marcar_sem_documento():
    paciente = PacienteCreate(**DADOS_BASE, num_cpf="52998224725")
    assert paciente.sem_documento is False
    assert paciente.num_cpf == "52998224725"
