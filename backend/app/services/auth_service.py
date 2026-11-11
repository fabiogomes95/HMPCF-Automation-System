import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, UnauthorizedError
from app.models.sessao import Sessao
from app.models.usuario import Usuario
from app.repositories.sessao_repository import SessaoRepository
from app.repositories.usuario_repository import UsuarioRepository


# Limite de senha errada POR COMPUTADOR (IP), não por conta: errar num PC não
# trava o "recepcao" nos outros (o bloqueio por conta saiu em 23/09/2026 por isso).
# 10 erros em 5 min -> aquele IP espera 1 min a cada nova tentativa.
LIMITE_FALHAS = 10
JANELA_FALHAS_S = 5 * 60
ESPERA_S = 60
_falhas_por_ip: dict[str, list[float]] = {}  # um processo só (uvicorn sem workers)


def _falhas_recentes(ip: str) -> list[float]:
    agora = time.monotonic()
    recentes = [t for t in _falhas_por_ip.get(ip, []) if agora - t < JANELA_FALHAS_S]
    if recentes:
        _falhas_por_ip[ip] = recentes
    else:
        _falhas_por_ip.pop(ip, None)
    return recentes


def _ip_em_espera(ip: Optional[str]) -> bool:
    if not ip:
        return False
    recentes = _falhas_recentes(ip)
    return len(recentes) >= LIMITE_FALHAS and time.monotonic() - recentes[-1] < ESPERA_S


def _registrar_falha(ip: Optional[str]) -> None:
    if ip:
        _falhas_recentes(ip)
        _falhas_por_ip.setdefault(ip, []).append(time.monotonic())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def conferir_senha(senha: str, password_hash: str) -> bool:
    """bcrypt leva ~0,2-0,3 s de propósito -- roda numa thread pra não parar
    o servidor inteiro (o uvicorn é um processo só) enquanto confere."""
    return await run_in_threadpool(bcrypt.checkpw, senha.encode("utf-8"), password_hash.encode("utf-8"))


async def gerar_hash_senha(senha: str) -> str:
    """Mesmo motivo de conferir_senha: o hash bcrypt roda fora do loop."""
    return (await run_in_threadpool(bcrypt.hashpw, senha.encode("utf-8"), bcrypt.gensalt())).decode()


def _aware(dt: datetime) -> datetime:
    """Garante datetime timezone-aware, assumindo UTC se vier naive.
    Defesa contra bancos/dialetos que não preservam timezone em
    DateTime(timezone=True) (ex.: SQLite) — no Postgres de produção
    (asyncpg) o valor já vem aware e isto é um no-op."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class AuthService:
    """
    Login por sessão em cookie httpOnly. O cookie guarda um token opaco
    aleatório; só o hash SHA-256 dele fica gravado em `sessoes` — uma
    leitura do banco não é suficiente pra forjar uma sessão válida.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._usuarios = UsuarioRepository(session)
        self._sessoes = SessaoRepository(session)

    async def autenticar(
        self, username: str, password: str, ip: Optional[str] = None, lembrar: bool = False
    ) -> tuple[Usuario, str]:
        """Confere credenciais e abre uma sessão nova. Retorna (usuario, token_bruto) —
        o token bruto só existe aqui, nunca é persistido."""
        if _ip_em_espera(ip):
            raise UnauthorizedError("Muitas tentativas erradas neste computador — aguarde 1 minuto")

        usuario = await self._usuarios.get_by_username(username)
        agora = datetime.now(timezone.utc)

        # Mensagem genérica em ambos os casos — não revela se o usuário existe.
        if usuario is None or not usuario.ativo:
            _registrar_falha(ip)
            raise UnauthorizedError("Usuário ou senha inválidos")

        # Sem bloqueio da CONTA por tentativas erradas (decisão de 23/09/2026):
        # o terminal fixo usa o mesmo usuário "recepcao" no auto-login, e errar
        # a senha em outro PC travava a recepção no meio do plantão. O limite
        # é por IP (ver _ip_em_espera).
        if not await conferir_senha(password, usuario.password_hash):
            _registrar_falha(ip)
            raise UnauthorizedError("Usuário ou senha inválidos")
        if ip:
            _falhas_por_ip.pop(ip, None)

        usuario.last_login_at = agora
        await self._sessoes.delete_expiradas()

        ttl_horas = settings.SESSION_TTL_LEMBRAR_HORAS if lembrar else settings.SESSION_TTL_HOURS
        token = secrets.token_urlsafe(32)
        sessao = Sessao(
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            expira_em=agora + timedelta(hours=ttl_horas),
            ip_criacao=ip,
        )
        self.session.add(sessao)
        await self.session.flush()
        return usuario, token

    async def usuario_para_auto_login(self, username: str) -> Optional[Usuario]:
        """Usado só pelo bypass de acesso local (ver app/api/deps.py) --
        mesma elegibilidade do login normal (conta ativa), mas sem senha.
        Quem decide SE o bypass se aplica (IP de origem, config) é o
        dependency, não este método. Atualiza last_login_at só nesta
        chamada -- ela só acontece quando não há sessão válida (cookie
        ausente/expirado), não a cada request."""
        usuario = await self._usuarios.get_by_username(username)
        if usuario is None or not usuario.ativo:
            return None
        usuario.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()
        return usuario

    async def validar_sessao(self, token: Optional[str]) -> Usuario:
        if not token:
            raise UnauthorizedError("Sessão ausente — faça login novamente")

        sessao = await self._sessoes.get_by_token_hash(_hash_token(token))
        agora = datetime.now(timezone.utc)
        if sessao is None or _aware(sessao.expira_em) < agora:
            raise UnauthorizedError("Sessão expirada — faça login novamente")
        if not sessao.usuario.ativo:
            raise UnauthorizedError("Conta desativada")
        return sessao.usuario

    async def alterar_senha(
        self, usuario: Usuario, senha_atual: str, senha_nova: str, token_atual: Optional[str] = None
    ) -> None:
        """Troca a senha e derruba os OUTROS logins desse usuário -- quem trocou
        (sessão de `token_atual`) continua logado."""
        # BusinessRuleError (422), não Unauthorized (401): 401 faz o frontend
        # derrubar a sessão, e errar a senha atual não é sessão inválida.
        if not await conferir_senha(senha_atual, usuario.password_hash):
            raise BusinessRuleError("Senha atual incorreta")
        if len(senha_nova or "") < 4:
            raise BusinessRuleError("Senha nova deve ter pelo menos 4 caracteres")
        usuario.password_hash = await gerar_hash_senha(senha_nova)
        await self._sessoes.delete_do_usuario(
            usuario.id, exceto_token_hash=_hash_token(token_atual) if token_atual else None
        )
        await self.session.flush()

    async def logout(self, token: Optional[str]) -> None:
        """Apaga a sessão correspondente, se existir. Nunca falha por token ausente/inválido."""
        if not token:
            return
        sessao = await self._sessoes.get_by_token_hash(_hash_token(token))
        if sessao is not None:
            await self._sessoes.delete(sessao)
