"""Endpoints exclusivos do perfil TI — gerenciamento de usuários e atendimentos."""
from datetime import datetime
from typing import Optional

import bcrypt
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import TIUser, DBSession
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.usuario import Usuario
from app.repositories.sessao_repository import SessaoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auditoria_service import AuditoriaService
from app.services.recepcao_service import RecepcaoService
from app.services.painel_service import Periodo, montar_painel

router = APIRouter()

ROLES_VALIDOS = ("recepcao", "faturamento", "ti")
SENHA_MIN = 4


def _checar_senha(senha: str) -> None:
    if len(senha or "") < SENHA_MIN:
        raise BusinessRuleError(f"Senha deve ter pelo menos {SENHA_MIN} caracteres")


class CriarUsuarioInput(BaseModel):
    username: str
    password: str
    role: str  # "recepcao" | "faturamento" | "ti"


class ResetarSenhaInput(BaseModel):
    nova_senha: str


class AtivoInput(BaseModel):
    ativo: bool


class UsuarioOut(BaseModel):
    id: int
    username: str
    role: str
    ativo: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/usuarios", response_model=list[UsuarioOut])
async def listar_usuarios(session: DBSession, _: TIUser) -> list[UsuarioOut]:
    repo = UsuarioRepository(session)
    users = await repo.list(order_by=Usuario.username)
    return [UsuarioOut.model_validate(u) for u in users]


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
async def criar_usuario(dados: CriarUsuarioInput, session: DBSession, usuario: TIUser) -> UsuarioOut:
    username = dados.username.strip()
    if not username:
        raise BusinessRuleError("Login é obrigatório")
    if dados.role not in ROLES_VALIDOS:
        raise BusinessRuleError(f"Perfil inválido: use {' ou '.join(ROLES_VALIDOS)}")
    _checar_senha(dados.password)
    repo = UsuarioRepository(session)
    if await repo.get_by_username(username):
        raise ConflictError(f"Usuário '{username}' já existe")
    pw_hash = bcrypt.hashpw(dados.password.encode(), bcrypt.gensalt()).decode()
    user = await repo.add(Usuario(username=username, password_hash=pw_hash, role=dados.role))
    await AuditoriaService(session).registrar(usuario, "criar", "usuario", user.id, campos_alterados=["role"])
    return UsuarioOut.model_validate(user)


@router.patch("/usuarios/{usuario_id}/senha")
async def resetar_senha(usuario_id: int, dados: ResetarSenhaInput, session: DBSession, usuario: TIUser) -> dict:
    _checar_senha(dados.nova_senha)
    repo = UsuarioRepository(session)
    user = await repo.get(usuario_id)
    if not user:
        raise NotFoundError("Usuário", usuario_id)
    user.password_hash = bcrypt.hashpw(dados.nova_senha.encode(), bcrypt.gensalt()).decode()
    # Senha resetada = quem estava logado com a senha antiga precisa entrar de novo.
    await SessaoRepository(session).delete_do_usuario(usuario_id)
    await session.flush()
    await AuditoriaService(session).registrar(usuario, "atualizar", "usuario", usuario_id, campos_alterados=["senha"])
    return {"status": "ok"}


@router.patch("/usuarios/{usuario_id}/ativo")
async def toggle_ativo(usuario_id: int, dados: AtivoInput, session: DBSession, usuario: TIUser) -> dict:
    if usuario_id == usuario.id and not dados.ativo:
        raise BusinessRuleError("Você não pode desativar a própria conta")
    repo = UsuarioRepository(session)
    user = await repo.get(usuario_id)
    if not user:
        raise NotFoundError("Usuário", usuario_id)
    user.ativo = dados.ativo
    if not dados.ativo:
        await SessaoRepository(session).delete_do_usuario(usuario_id)
    await session.flush()
    await AuditoriaService(session).registrar(usuario, "atualizar", "usuario", usuario_id, campos_alterados=["ativo"])
    return {"status": "ok"}


# ── Atendimentos ─────────────────────────────────────────────────────────────

@router.delete("/atendimentos/{atendimento_id}", status_code=200)
async def excluir_atendimento(atendimento_id: int, session: DBSession, usuario: TIUser) -> dict:
    """Exclui um atendimento pelo ID (somente TI) -- registrado na auditoria."""
    await RecepcaoService(session, usuario).remover(atendimento_id)
    return {"status": "ok"}


# ── Painel gerencial ─────────────────────────────────────────────────────────

@router.get("/painel")
async def painel(session: DBSession, _: TIUser, periodo: Periodo = Query("30d")) -> dict:
    """Agregados da recepção (substitui o antigo dashboard Streamlit) -- só números, nenhum dado pessoal."""
    return await montar_painel(session, periodo)
