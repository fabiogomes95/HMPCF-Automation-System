"""Conferência da planilha da recepção (aba BPA › Migração): lê o .xlsx das
meninas, acha o que não está no sistema e lança (paciente novo + entrada)."""
import io
from datetime import date, datetime, time

import openpyxl
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.importacao.conferencia_planilha import (
    AtendimentoSistema,
    faltando_no_sistema,
    ler_planilha,
    separar_endereco,
)
from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.services.conferencia_planilha_service import ConferenciaPlanilhaService
from app.services.recepcao_service import _FUSO_HOSPITAL

CPF_NOVO = "52998224725"     # válido
CPF_NOVO_2 = "11144477735"   # válido


def _linha(n, nome, nasc, sexo, hora, cpf="", sus="", endereco="", telefone=""):
    return [n, nome, nasc, None, sexo, "PARDA", "EXTREMOZ", hora, cpf, sus, None, endereco, telefone]


def _xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "OUTUBRO 2026"
    ws.append(["PLANTÃO DIURNO 01/10/2026 - FULANA"])
    ws.append(_linha(1, "MARIA SILVA", datetime(1990, 1, 1), "F", time(8, 0), "123.456.789-01"))      # já lançada
    ws.append(_linha(2, "JOAO SANTOS", datetime(1985, 5, 15), "M", time(9, 30), "987.654.321-00"))    # só falta a entrada
    ws.append(_linha(3, "ANA NOVA DE SOUZA", datetime(2000, 2, 3), "F", time(10, 15),
                     "529.982.247-25", "", "R. DAS FLORES, 12 - CENTRO", "(84) 99123-4567"))     # paciente novo
    ws.append(_linha(4, "CARLA SEM NASCIMENTO", None, "F", time(11, 0), "111.444.777-35",
                     "", "RUA A, 1 - CENTRO"))                                                         # pendente
    ws.append([5, "FULANO SO NOME", None, None, None, None, None, time(12, 0)])                      # só nome
    ws.append(_linha(6, "PACIENTE SEM DOCUMENTO", None, None, time(13, 0), endereco="VILA DE FATIMA"))  # genérico
    ws.append(["PLANTÃO NOTURNO 01/10/2026 - BELTRANA"])
    ws.append(_linha(1, "ANA NOVA DE SOUZA", datetime(2000, 2, 3), "F", time(22, 40), "529.982.247-25"))  # voltou
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_separar_endereco():
    assert separar_endereco("R. DAS FLORES, 12 - CENTRO") == ("R. DAS FLORES", "12", "CENTRO")
    assert separar_endereco("VILA DE FATIMA") == ("VILA DE FATIMA", None, None)
    assert separar_endereco(None) == (None, None, None)


def test_ler_planilha_campos_extras():
    leitura = ler_planilha(_xlsx())
    assert leitura.abas_lidas == ["OUTUBRO 2026"]
    ana = next(ln for ln in leitura.linhas if ln.nome == "ANA NOVA DE SOUZA")
    assert (ana.registro, ana.sexo, ana.raca, ana.municipio, ana.telefone) == (3, "F", "03", "EXTREMOZ", "84991234567")
    assert ana.entrada.cpf == CPF_NOVO and ana.data == date(2026, 10, 1)


def test_paciente_que_voltou_no_dia_seguinte_nao_some():
    """Duas vindas na planilha e só a primeira no sistema: a segunda falta."""
    leitura = ler_planilha(_xlsx())
    ana = [ln for ln in leitura.linhas if ln.nome == "ANA NOVA DE SOUZA"]
    sistema = [AtendimentoSistema(1, datetime(2026, 10, 1, 10, 15), CPF_NOVO, None, "ANA NOVA DE SOUZA")]
    faltando = faltando_no_sistema(ana, sistema)
    assert [ln.hora for ln in faltando] == [time(22, 40)]


async def _contar(session, modelo):
    return (await session.execute(select(func.count()).select_from(modelo))).scalar_one()


@pytest.mark.asyncio
async def test_conferir_e_lancar(session: AsyncSession, paciente: Paciente, paciente2: Paciente):
    session.add(RecepcaoAtendimento(paciente_id=paciente.id,
                                    data_atendimento=datetime(2026, 10, 1, 8, 0, tzinfo=_FUSO_HOSPITAL)))
    await session.flush()
    svc = ConferenciaPlanilhaService(session)

    # 1) só confere: nada gravado
    r = await svc.executar(_xlsx())
    assert r["linhas_lidas"] == 7
    assert r["resumo"] == {"faltando": 6, "entrada": 2, "novo": 1, "pendente": 1, "ignorada": 2}
    por_nome = {i["nome"]: i for i in r["itens"]}
    assert "nascimento" in por_nome["CARLA SEM NASCIMENTO"]["motivo"].lower()
    assert por_nome["FULANO SO NOME"]["motivo"] == "só tem o nome"
    assert por_nome["PACIENTE SEM DOCUMENTO"]["motivo"] == "nome genérico"
    assert await _contar(session, Paciente) == 2 and await _contar(session, RecepcaoAtendimento) == 1

    # 2) lança: Ana cadastrada uma vez só, com as duas vindas; João ganha a entrada
    r = await svc.executar(_xlsx(), aplicar=True)
    assert r["resumo"]["pacientes_criados"] == 1
    assert r["resumo"]["entradas_lancadas"] == 3
    assert r["resumo"]["erros"] == 0
    ana = (await session.execute(select(Paciente).where(Paciente.num_cpf == CPF_NOVO))).scalar_one()
    assert (ana.dtnasc, ana.sexo, ana.logpcn, ana.numpcn, ana.bairro_pcnte, ana.ddtel_pcnte, ana.tel_pcnte) == \
        ("20000203", "F", "R. DAS FLORES", "12", "CENTRO", "84", "991234567")
    atd_joao = (await session.execute(select(RecepcaoAtendimento).where(
        RecepcaoAtendimento.paciente_id == paciente2.id))).scalar_one()
    assert atd_joao.data_atendimento == datetime(2026, 10, 1, 9, 30, tzinfo=_FUSO_HOSPITAL)
    assert atd_joao.registro == 2

    # 3) rodar de novo não duplica nada
    r = await svc.executar(_xlsx(), aplicar=True)
    assert r["resumo"]["faltando"] == 3  # só pendente e ignoradas
    assert r["resumo"].get("pacientes_criados") == 0 and r["resumo"]["entradas_lancadas"] == 0
    assert await _contar(session, Paciente) == 3 and await _contar(session, RecepcaoAtendimento) == 4


@pytest.mark.asyncio
async def test_arquivo_invalido(session: AsyncSession):
    from app.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await ConferenciaPlanilhaService(session).executar(b"nao e xlsx")
    with pytest.raises(ValidationError):
        await ConferenciaPlanilhaService(session).executar(b"")
