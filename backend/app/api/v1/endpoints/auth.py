from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.schemas.auth import LoginRequest, UsuarioResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=UsuarioResponse, summary="Login por usuário/senha (papel)")
async def login(
    dados: LoginRequest,
    request: Request,
    response: Response,
    session: DBSession,
) -> UsuarioResponse:
    ip = request.client.host if request.client else None
    usuario, token = await AuthService(session).autenticar(dados.username, dados.password, ip=ip)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # sistema roda em HTTP puro na LAN do hospital, sem TLS ainda
    )
    return UsuarioResponse.model_validate(usuario)


@router.post("/logout", summary="Encerra a sessão atual")
async def logout(request: Request, response: Response, session: DBSession) -> dict:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    await AuthService(session).logout(token)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"status": "ok"}


@router.get("/me", response_model=UsuarioResponse, summary="Usuário da sessão atual")
async def me(usuario: CurrentUser) -> UsuarioResponse:
    return UsuarioResponse.model_validate(usuario)
