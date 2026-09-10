from typing import Annotated, Optional

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auth_service import AuthService

# Tipo anotado para injeção de sessão nos endpoints.
# Uso: async def endpoint(session: DBSession) -> ...
DBSession = Annotated[AsyncSession, Depends(get_db)]

_HOSTS_LOOPBACK = {"127.0.0.1", "::1"}


async def get_current_user(
    request: Request,
    session: DBSession,
    session_token: Annotated[Optional[str], Cookie(alias=settings.SESSION_COOKIE_NAME)] = None,
) -> Usuario:
    """Lê o cookie de sessão e valida contra a tabela `sessoes`.
    Levanta UnauthorizedError (→ 401) se ausente/expirada/inválida.

    Exceção: acesso feito por loopback (a própria máquina, sem cookie de
    sessão ainda) usa direto AUTO_LOGIN_USERNAME em vez de pedir login —
    é assim que o terminal fixo da recepção abre sem tela de login. Quem
    acessa de outra máquina pela rede sempre tem um IP de origem diferente
    de loopback, então cai no fluxo de login normal."""
    is_loopback = request.client is not None and request.client.host in _HOSTS_LOOPBACK
    if settings.AUTO_LOGIN_LOCAL and is_loopback and not session_token:
        usuario = await UsuarioRepository(session).get_by_username(settings.AUTO_LOGIN_USERNAME)
        if usuario is not None and usuario.ativo:
            return usuario
    return await AuthService(session).validar_sessao(session_token)


# Tipo anotado para exigir sessão válida num endpoint.
# Uso: async def endpoint(session: DBSession, usuario: CurrentUser) -> ...
CurrentUser = Annotated[Usuario, Depends(get_current_user)]
