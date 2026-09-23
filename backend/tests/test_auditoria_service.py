import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_auditoria import LogAuditoria
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.schemas.paciente import PacienteCreate, PacienteUpdate
from app.schemas.recepcao import RecepcaoCreate, RecepcaoUpdate
from app.services.paciente_service import PacienteService
from app.services.recepcao_service import RecepcaoService


async def _criar_usuario_teste(session: AsyncSession, username: str = "teste_auditoria") -> Usuario:
    usuario = Usuario(username=username, password_hash="hash-nao-importa-aqui", role="recepcao")
    session.add(usuario)
    await session.flush()
    await session.refresh(usuario)
    return usuario


async def _logs(session: AsyncSession) -> list[LogAuditoria]:
    result = await session.execute(select(LogAuditoria))
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
async def test_listar_e_obter_nao_geram_log(session: AsyncSession):
    usuario = await _criar_usuario_teste(session)
    svc = PacienteService(session, usuario)

    resposta = await svc.criar(
        PacienteCreate(nome="ANA AUDITADA", num_cpf="50443332479", sexo="F", dtnasc="19900101")
    )
    logs_apos_criar = await _logs(session)

    await svc.listar(q=None, page=1, page_size=20)
    await svc.obter(resposta.id)

    logs_apos_leitura = await _logs(session)
    assert len(logs_apos_leitura) == len(logs_apos_criar)


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
