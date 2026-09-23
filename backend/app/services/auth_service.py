import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, UnauthorizedError
from app.models.sessao import Sessao
from app.models.usuario import Usuario
from app.repositories.sessao_repository import SessaoRepository
from app.repositories.usuario_repository import UsuarioRepository


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
        usuario = await self._usuarios.get_by_username(username)
        agora = datetime.now(timezone.utc)

        # Mensagem genérica em ambos os casos — não revela se o usuário existe.
        if usuario is None or not usuario.ativo:
            raise UnauthorizedError("Usuário ou senha inválidos")

        # Sem bloqueio por tentativas erradas (decisão de 23/09/2026): o
        # terminal fixo usa o mesmo usuário "recepcao" no auto-login, e errar
        # a senha em outro PC travava a recepção no meio do plantão.
        senha_ok = bcrypt.checkpw(
            password.encode("utf-8"), usuario.password_hash.encode("utf-8")
        )
        if not senha_ok:
            raise UnauthorizedError("Usuário ou senha inválidos")

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

    async def alterar_senha(self, usuario: Usuario, senha_atual: str, senha_nova: str) -> None:
        # BusinessRuleError (422), não Unauthorized (401): 401 faz o frontend
        # derrubar a sessão, e errar a senha atual não é sessão inválida.
        if not bcrypt.checkpw(senha_atual.encode("utf-8"), usuario.password_hash.encode("utf-8")):
            raise BusinessRuleError("Senha atual incorreta")
        if len(senha_nova or "") < 4:
            raise BusinessRuleError("Senha nova deve ter pelo menos 4 caracteres")
        usuario.password_hash = bcrypt.hashpw(senha_nova.encode("utf-8"), bcrypt.gensalt()).decode()
        await self.session.flush()

    async def logout(self, token: Optional[str]) -> None:
        """Apaga a sessão correspondente, se existir. Nunca falha por token ausente/inválido."""
        if not token:
            return
        sessao = await self._sessoes.get_by_token_hash(_hash_token(token))
        if sessao is not None:
            await self._sessoes.delete(sessao)
