from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.models.sessao import Sessao
from app.models.usuario import Usuario
from app.services.auth_service import AuthService, _hash_token

SENHA_PADRAO = "senha-forte-123"


async def _criar_usuario(
    session: AsyncSession, username: str, senha: str = SENHA_PADRAO, role: str = "recepcao"
) -> Usuario:
    usuario = Usuario(
        username=username,
        password_hash=bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        role=role,
    )
    session.add(usuario)
    await session.flush()
    await session.refresh(usuario)
    return usuario


@pytest.mark.asyncio
async def test_autenticar_login_correto(session: AsyncSession):
    await _criar_usuario(session, "teste_login_ok")
    svc = AuthService(session)

    usuario, token = await svc.autenticar("teste_login_ok", SENHA_PADRAO)

    assert usuario.username == "teste_login_ok"
    assert token
    assert usuario.last_login_at is not None


@pytest.mark.asyncio
async def test_autenticar_usuario_inexistente(session: AsyncSession):
    svc = AuthService(session)
    with pytest.raises(UnauthorizedError):
        await svc.autenticar("nao_existe", SENHA_PADRAO)


@pytest.mark.asyncio
async def test_autenticar_senha_errada(session: AsyncSession):
    await _criar_usuario(session, "teste_senha_errada")
    svc = AuthService(session)

    with pytest.raises(UnauthorizedError):
        await svc.autenticar("teste_senha_errada", "senha-errada")


@pytest.mark.asyncio
async def test_autenticar_nao_bloqueia_apos_erros(session: AsyncSession):
    # Sem bloqueio por tentativas: errar a senha em outro PC não pode travar
    # o usuário "recepcao", que o terminal fixo usa no auto-login.
    await _criar_usuario(session, "teste_sem_bloqueio")
    svc = AuthService(session)

    for _ in range(10):
        with pytest.raises(UnauthorizedError):
            await svc.autenticar("teste_sem_bloqueio", "senha-errada")

    usuario, token = await svc.autenticar("teste_sem_bloqueio", SENHA_PADRAO)
    assert token


@pytest.mark.asyncio
async def test_validar_sessao_sem_token(session: AsyncSession):
    svc = AuthService(session)
    with pytest.raises(UnauthorizedError):
        await svc.validar_sessao(None)


@pytest.mark.asyncio
async def test_validar_sessao_expirada(session: AsyncSession):
    usuario = await _criar_usuario(session, "teste_sessao_expirada")
    sessao = Sessao(
        usuario_id=usuario.id,
        token_hash=_hash_token("token-de-teste-expirado"),
        expira_em=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    session.add(sessao)
    await session.flush()

    svc = AuthService(session)
    with pytest.raises(UnauthorizedError):
        await svc.validar_sessao("token-de-teste-expirado")


@pytest.mark.asyncio
async def test_logout_invalida_sessao(session: AsyncSession):
    await _criar_usuario(session, "teste_logout")
    svc = AuthService(session)

    _, token = await svc.autenticar("teste_logout", SENHA_PADRAO)
    usuario_validado = await svc.validar_sessao(token)
    assert usuario_validado.username == "teste_logout"

    await svc.logout(token)

    with pytest.raises(UnauthorizedError):
        await svc.validar_sessao(token)


@pytest.mark.asyncio
async def test_logout_sem_token_nao_falha(session: AsyncSession):
    svc = AuthService(session)
    await svc.logout(None)  # não deve levantar exceção


@pytest.fixture
def _sem_falhas_registradas():
    from app.services import auth_service
    auth_service._falhas_por_ip.clear()
    yield
    auth_service._falhas_por_ip.clear()


@pytest.mark.asyncio
async def test_ip_com_muitos_erros_espera_mas_conta_continua_livre(session: AsyncSession, _sem_falhas_registradas):
    """10 erros do mesmo IP -> esse IP espera; a conta entra normalmente de outro IP."""
    await _criar_usuario(session, "teste_limite_ip")
    svc = AuthService(session)

    for _ in range(10):
        with pytest.raises(UnauthorizedError, match="inválidos"):
            await svc.autenticar("teste_limite_ip", "senha-errada", ip="10.0.0.5")

    # mesmo IP: recusado até com a senha certa
    with pytest.raises(UnauthorizedError, match="aguarde"):
        await svc.autenticar("teste_limite_ip", SENHA_PADRAO, ip="10.0.0.5")

    # outro computador: entra
    usuario, token = await svc.autenticar("teste_limite_ip", SENHA_PADRAO, ip="10.0.0.6")
    assert token


@pytest.mark.asyncio
async def test_usuario_inexistente_tambem_conta_no_limite(session: AsyncSession, _sem_falhas_registradas):
    svc = AuthService(session)
    for _ in range(10):
        with pytest.raises(UnauthorizedError):
            await svc.autenticar("chute_qualquer", "x", ip="10.0.0.7")
    with pytest.raises(UnauthorizedError, match="aguarde"):
        await svc.autenticar("chute_qualquer", "x", ip="10.0.0.7")


@pytest.mark.asyncio
async def test_espera_acaba_depois_de_1_minuto(session: AsyncSession, _sem_falhas_registradas, monkeypatch):
    from app.services import auth_service

    await _criar_usuario(session, "teste_espera_acaba")
    svc = AuthService(session)
    agora = [1000.0]
    monkeypatch.setattr(auth_service.time, "monotonic", lambda: agora[0])

    for _ in range(10):
        with pytest.raises(UnauthorizedError):
            await svc.autenticar("teste_espera_acaba", "senha-errada", ip="10.0.0.8")
    agora[0] += auth_service.ESPERA_S + 1
    usuario, token = await svc.autenticar("teste_espera_acaba", SENHA_PADRAO, ip="10.0.0.8")
    assert token


@pytest.mark.asyncio
async def test_trocar_senha_derruba_os_outros_logins_e_mantem_o_atual(session: AsyncSession):
    usuario = await _criar_usuario(session, "teste_troca_senha")
    svc = AuthService(session)
    _, token_deste_pc = await svc.autenticar("teste_troca_senha", SENHA_PADRAO)
    _, token_outro_pc = await svc.autenticar("teste_troca_senha", SENHA_PADRAO)

    await svc.alterar_senha(usuario, SENHA_PADRAO, "senha-nova-456", token_atual=token_deste_pc)

    assert (await svc.validar_sessao(token_deste_pc)).username == "teste_troca_senha"
    with pytest.raises(UnauthorizedError):
        await svc.validar_sessao(token_outro_pc)
    _, token = await svc.autenticar("teste_troca_senha", "senha-nova-456")
    assert token
