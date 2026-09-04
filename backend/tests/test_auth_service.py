from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
    assert usuario.tentativas_falhas == 0
    assert usuario.last_login_at is not None


@pytest.mark.asyncio
async def test_autenticar_usuario_inexistente(session: AsyncSession):
    svc = AuthService(session)
    with pytest.raises(UnauthorizedError):
        await svc.autenticar("nao_existe", SENHA_PADRAO)


@pytest.mark.asyncio
async def test_autenticar_senha_errada(session: AsyncSession):
    usuario = await _criar_usuario(session, "teste_senha_errada")
    svc = AuthService(session)

    with pytest.raises(UnauthorizedError):
        await svc.autenticar("teste_senha_errada", "senha-errada")

    await session.refresh(usuario)
    assert usuario.tentativas_falhas == 1


@pytest.mark.asyncio
async def test_autenticar_bloqueia_apos_max_tentativas(session: AsyncSession):
    usuario = await _criar_usuario(session, "teste_bloqueio")
    svc = AuthService(session)

    for _ in range(settings.LOGIN_MAX_TENTATIVAS):
        with pytest.raises(UnauthorizedError):
            await svc.autenticar("teste_bloqueio", "senha-errada")

    await session.refresh(usuario)
    assert usuario.bloqueado_ate is not None

    # Mesmo com a senha certa, continua bloqueado até o prazo passar.
    with pytest.raises(UnauthorizedError):
        await svc.autenticar("teste_bloqueio", SENHA_PADRAO)


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
