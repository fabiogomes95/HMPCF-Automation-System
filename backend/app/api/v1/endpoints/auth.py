from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.schemas.auth import LoginRequest, UsuarioResponse
from app.services.auditoria_service import AuditoriaService
from app.services.auth_service import AuthService


class AlterarSenhaInput(BaseModel):
    senha_atual: str
    senha_nova: str

router = APIRouter()


@router.post("/login", response_model=UsuarioResponse, summary="Login por usuário/senha (papel)")
async def login(
    dados: LoginRequest,
    request: Request,
    response: Response,
    session: DBSession,
) -> UsuarioResponse:
    ip = request.client.host if request.client else None
    usuario, token = await AuthService(session).autenticar(
        dados.username, dados.password, ip=ip, lembrar=dados.lembrar
    )
    ttl_horas = settings.SESSION_TTL_LEMBRAR_HORAS if dados.lembrar else settings.SESSION_TTL_HOURS
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl_horas * 3600,
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


@router.post("/change-password", summary="Alterar própria senha")
async def change_password(dados: AlterarSenhaInput, usuario: CurrentUser, session: DBSession) -> dict:
    await AuthService(session).alterar_senha(usuario, dados.senha_atual, dados.senha_nova)
    await AuditoriaService(session).registrar(usuario, "atualizar", "usuario", usuario.id, campos_alterados=["senha"])
    return {"status": "ok"}
