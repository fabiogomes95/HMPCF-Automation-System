from typing import Annotated, Optional

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.database.session import get_db
from app.models.usuario import Usuario
from app.services.auth_service import AuthService

# Tipo anotado para injeção de sessão nos endpoints.
# Uso: async def endpoint(session: DBSession) -> ...
DBSession = Annotated[AsyncSession, Depends(get_db)]

_HOSTS_LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
# Sec-Fetch-Site que o navegador manda em toda fetch/XHR moderna: "same-origin"
# quando quem chamou é a própria aplicação, ausente/"none" quando não é
# navegador (script local, curl). "cross-site" é uma aba de OUTRO site
# chamando a API local -- isso não deve entrar pelo bypass.
_SEC_FETCH_SITE_CONFIAVEIS = {None, "same-origin", "none"}


def _auto_login_elegivel(request: Request) -> bool:
    if not settings.AUTO_LOGIN_LOCAL:
        return False
    if request.client is None or request.client.host not in _HOSTS_LOOPBACK:
        return False
    return request.headers.get("sec-fetch-site") in _SEC_FETCH_SITE_CONFIAVEIS


async def get_current_user(
    request: Request,
    session: DBSession,
    session_token: Annotated[Optional[str], Cookie(alias=settings.SESSION_COOKIE_NAME)] = None,
) -> Usuario:
    """Lê o cookie de sessão e valida contra a tabela `sessoes`.
    Levanta UnauthorizedError (→ 401) se ausente/expirada/inválida.

    Exceção: acesso elegível pro auto-login local (loopback, AUTO_LOGIN_LOCAL
    ligado, chamada não veio de outra página via fetch/XHR cross-site) usa
    AUTO_LOGIN_USERNAME sempre que não há sessão válida -- cookie ausente OU
    expirado/inválido -- é assim que o terminal fixo da recepção nunca trava
    na tela de login, mesmo depois do cookie expirar. Quem acessa de outra
    máquina pela rede sempre tem um IP de origem diferente de loopback, então
    cai no fluxo de login normal."""
    auth = AuthService(session)
    try:
        return await auth.validar_sessao(session_token)
    except UnauthorizedError:
        if not _auto_login_elegivel(request):
            raise
        usuario = await auth.usuario_para_auto_login(settings.AUTO_LOGIN_USERNAME)
        if usuario is None:
            raise
        return usuario


# Tipo anotado para exigir sessão válida num endpoint.
# Uso: async def endpoint(session: DBSession, usuario: CurrentUser) -> ...
CurrentUser = Annotated[Usuario, Depends(get_current_user)]
