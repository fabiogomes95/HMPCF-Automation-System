from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auditoria import listar_auditoria
from app.models.log_auditoria import LogAuditoria
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.schemas.paciente import PacienteCreate, PacienteUpdate
from app.schemas.recepcao import RecepcaoCreate, RecepcaoUpdate
from app.services.auditoria_service import AuditoriaService
from app.services.paciente_service import PacienteService
from app.services.recepcao_service import RecepcaoService


async def _criar_usuario_teste(session: AsyncSession, username: str = "teste_auditoria") -> Usuario:
    usuario = Usuario(username=username, password_hash="hash-nao-importa-aqui", role="recepcao")
    session.add(usuario)
    await session.flush()
    await session.refresh(usuario)
    return usuario


async def _logs(session: AsyncSession) -> list[LogAuditoria]:
    result = await session.execute(select(LogAuditoria).order_by(LogAuditoria.id))
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_criar_paciente_gera_log(session: AsyncSession):
    usuario = await _criar_usuario_teste(session)
    svc = PacienteService(session, usuario)

    resposta = await svc.criar(
        PacienteCreate(nome="MARIA AUDITADA", num_cpf="15094095307", sexo="F", dtnasc="19900101")
    )

    logs = await _logs(session)
    assert len(logs) == 1
    assert logs[0].acao == "criar"
    assert logs[0].recurso == "paciente"
    assert logs[0].recurso_id == resposta.id
    assert logs[0].usuario_username == "teste_auditoria"
    assert logs[0].campos_alterados is None


@pytest.mark.asyncio
async def test_atualizar_paciente_gera_log_com_campos_alterados(session: AsyncSession):
    usuario = await _criar_usuario_teste(session)
    svc = PacienteService(session, usuario)

    resposta = await svc.criar(
        PacienteCreate(nome="JOAO AUDITADO", num_cpf="44553368420", sexo="M", dtnasc="19900101")
    )
    await svc.atualizar(resposta.id, PacienteUpdate(nome="JOAO AUDITADO EDITADO", cidade="EXTREMOZ"))

    logs = await _logs(session)
    log_update = next(log for log in logs if log.acao == "atualizar")
    assert log_update.recurso == "paciente"
    assert log_update.recurso_id == resposta.id
    assert set(log_update.campos_alterados) == {"nome", "cidade"}


@pytest.mark.asyncio
async def test_remover_paciente_gera_log(session: AsyncSession):
    usuario = await _criar_usuario_teste(session)
    svc = PacienteService(session, usuario)

    resposta = await svc.criar(
        PacienteCreate(nome="PEDRO AUDITADO", num_cpf="65072388646", sexo="M", dtnasc="19900101")
    )
    await svc.remover(resposta.id)

    logs = await _logs(session)
    log_remocao = next(log for log in logs if log.acao == "remover")
    assert log_remocao.recurso_id == resposta.id
    assert log_remocao.campos_alterados is None


@pytest.mark.asyncio
async def test_consultas_ao_paciente_geram_log_e_lista_por_nome_nao(session: AsyncSession):
    """LGPD: abrir a ficha/histórico e achar por CPF/CNS ficam registrados;
    lista por nome não (seria 1 linha por paciente da lista)."""
    usuario = await _criar_usuario_teste(session)
    svc = PacienteService(session, usuario)
    resposta = await svc.criar(
        PacienteCreate(nome="ANA AUDITADA", num_cpf="50443332479", sexo="F", dtnasc="19900101")
    )
    antes = len(await _logs(session))

    await svc.listar(q="ANA", page=1, page_size=20)
    assert len(await _logs(session)) == antes

    await svc.obter(resposta.id)
    await svc.buscar_por_documento("504.433.324-79")
    recepcao = RecepcaoService(session, usuario)
    await recepcao.listar_por_paciente(resposta.id, page=1, page_size=10)
    await recepcao.listar_por_paciente(resposta.id, page=2, page_size=10)  # mesma abertura, outra página

    novos = (await _logs(session))[antes:]
    assert [(l.acao, l.recurso, l.recurso_id) for l in novos] == [
        ("consultar", "paciente", resposta.id),
        ("buscar_doc", "paciente", resposta.id),
        ("consultar", "paciente", resposta.id),
    ]


@pytest.mark.asyncio
async def test_consultas_com_mais_de_1_ano_saem_e_escritas_ficam(session: AsyncSession):
    usuario = await _criar_usuario_teste(session)
    velho = datetime.now(timezone.utc) - timedelta(days=400)
    recente = datetime.now(timezone.utc) - timedelta(days=30)
    for acao, quando in [("consultar", velho), ("buscar_doc", velho), ("consultar", recente), ("atualizar", velho)]:
        session.add(LogAuditoria(usuario_id=usuario.id, usuario_username=usuario.username,
                                 acao=acao, recurso="paciente", recurso_id=1, criado_em=quando))
    await session.flush()

    assert await AuditoriaService(session).apagar_consultas_antigas() == 2
    session.expire_all()
    assert sorted(l.acao for l in await _logs(session)) == ["atualizar", "consultar"]


@pytest.mark.asyncio
async def test_filtro_por_paciente_traz_consultas_cadastro_e_atendimentos_dele(
    session: AsyncSession, paciente: Paciente, paciente2: Paciente,
):
    ti = await _criar_usuario_teste(session, "teste_ti_filtro")
    usuario = await _criar_usuario_teste(session, "teste_recepcao_filtro")
    recepcao = RecepcaoService(session, usuario)
    atd = await recepcao.criar(RecepcaoCreate(paciente_id=paciente.id))
    await PacienteService(session, usuario).buscar_por_documento(paciente.num_cpf)
    await PacienteService(session, usuario).buscar_por_documento(paciente2.num_cpf)  # outro paciente

    res = await listar_auditoria(session, ti, recurso=None, recurso_id=None, acao=None,
                                 paciente_documento=paciente.cns, usuario_username=None,
                                 desde=None, ate=None, page=1, page_size=20)
    assert {(i.acao, i.recurso, i.recurso_id) for i in res.items} == {
        ("criar", "atendimento", atd.id), ("buscar_doc", "paciente", paciente.id),
    }
    nenhum = await listar_auditoria(session, ti, recurso=None, recurso_id=None, acao=None,
                                    paciente_documento="00000000000", usuario_username=None,
                                    desde=None, ate=None, page=1, page_size=20)
    assert nenhum.total == 0


@pytest.mark.asyncio
async def test_usuario_none_nao_gera_log(session: AsyncSession):
    svc = PacienteService(session)  # sem usuario -- mesma construção dos testes antigos

    await svc.criar(
        PacienteCreate(nome="SEM USUARIO", num_cpf="95549514770", sexo="F", dtnasc="19900101")
    )

    logs = await _logs(session)
    assert logs == []


@pytest.mark.asyncio
async def test_criar_atendimento_gera_log(session: AsyncSession, paciente: Paciente):
    usuario = await _criar_usuario_teste(session)
    svc = RecepcaoService(session, usuario)

    resposta = await svc.criar(RecepcaoCreate(paciente_id=paciente.id))

    logs = await _logs(session)
    assert len(logs) == 1
    assert logs[0].acao == "criar"
    assert logs[0].recurso == "atendimento"
    assert logs[0].recurso_id == resposta.id


@pytest.mark.asyncio
async def test_atualizar_e_remover_atendimento_geram_log(session: AsyncSession, paciente: Paciente):
    usuario = await _criar_usuario_teste(session)
    svc = RecepcaoService(session, usuario)

    resposta = await svc.criar(RecepcaoCreate(paciente_id=paciente.id))
    await svc.atualizar(resposta.id, RecepcaoUpdate(procedencia="UBS CENTRO"))
    await svc.remover(resposta.id)

    logs = await _logs(session)
    acoes = [log.acao for log in logs]
    assert acoes == ["criar", "atualizar", "remover"]
    assert logs[1].campos_alterados == ["procedencia"]


@pytest.mark.asyncio
async def test_gestao_de_usuarios_gera_log_sem_senha(session: AsyncSession):
    # Endpoints da TI chamados direto (sem HTTP): criar, resetar senha e desativar
    # conta ficam na auditoria -- só metadados, a senha nunca vai pro log.
    from app.api.v1.endpoints.ti import (
        AtivoInput, CriarUsuarioInput, ResetarSenhaInput, criar_usuario, resetar_senha, toggle_ativo,
    )

    ti = await _criar_usuario_teste(session, "teste_ti_auditoria")
    ti.role = "ti"
    novo = await criar_usuario(
        CriarUsuarioInput(username="teste_novo_usuario", password="senha-secreta-1", role="recepcao"),
        session, ti,
    )
    await resetar_senha(novo.id, ResetarSenhaInput(nova_senha="senha-secreta-2"), session, ti)
    await toggle_ativo(novo.id, AtivoInput(ativo=False), session, ti)

    logs = [l for l in await _logs(session) if l.recurso == "usuario"]
    assert [(l.acao, l.recurso_id, l.campos_alterados) for l in logs] == [
        ("criar", novo.id, ["role"]),
        ("atualizar", novo.id, ["senha"]),
        ("atualizar", novo.id, ["ativo"]),
    ]
    assert all(l.usuario_username == "teste_ti_auditoria" for l in logs)
    assert "senha-secreta" not in repr([(l.acao, l.campos_alterados) for l in logs])


@pytest.mark.asyncio
async def test_faturamento_criado_mas_barrado_nas_rotas_da_ti(session: AsyncSession):
    # Faturamento registra/edita atendimentos (rotas CurrentUser), mas excluir,
    # usuários, auditoria e painel exigem TI -- o servidor recusa, não só a tela.
    from app.api.deps import get_ti_user
    from app.api.v1.endpoints.ti import CriarUsuarioInput, criar_usuario
    from app.core.exceptions import ForbiddenError

    ti = await _criar_usuario_teste(session, "teste_ti_fat")
    ti.role = "ti"
    fat = await criar_usuario(
        CriarUsuarioInput(username="teste_faturamento", password="senha-fat-1", role="faturamento"),
        session, ti,
    )
    assert fat.role == "faturamento"

    usuario_fat = await session.get(Usuario, fat.id)
    with pytest.raises(ForbiddenError):
        await get_ti_user(usuario_fat)
    assert await get_ti_user(ti) is ti
