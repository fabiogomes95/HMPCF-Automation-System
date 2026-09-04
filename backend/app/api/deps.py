from typing import Annotated, Optional

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.models.usuario import Usuario
from app.services.auth_service import AuthService

# Tipo anotado para injeção de sessão nos endpoints.
# Uso: async def endpoint(session: DBSession) -> ...
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: DBSession,
    session_token: Annotated[Optional[str], Cookie(alias=settings.SESSION_COOKIE_NAME)] = None,
) -> Usuario:
    """Lê o cookie de sessão e valida contra a tabela `sessoes`.
    Levanta UnauthorizedError (→ 401) se ausente/expirada/inválida."""
    return await AuthService(session).validar_sessao(session_token)


# Tipo anotado para exigir sessão válida num endpoint.
# Uso: async def endpoint(session: DBSession, usuario: CurrentUser) -> ...
CurrentUser = Annotated[Usuario, Depends(get_current_user)]
