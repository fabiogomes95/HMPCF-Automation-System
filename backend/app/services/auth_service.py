import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
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
        self, username: str, password: str, ip: Optional[str] = None
    ) -> tuple[Usuario, str]:
        """Confere credenciais e abre uma sessão nova. Retorna (usuario, token_bruto) —
        o token bruto só existe aqui, nunca é persistido."""
        usuario = await self._usuarios.get_by_username(username)
        agora = datetime.now(timezone.utc)

        # Mensagem genérica em ambos os casos — não revela se o usuário existe.
        if usuario is None or not usuario.ativo:
            raise UnauthorizedError("Usuário ou senha inválidos")

        if usuario.bloqueado_ate and _aware(usuario.bloqueado_ate) > agora:
            raise UnauthorizedError(
                "Conta bloqueada por tentativas incorretas. "
                f"Tente novamente após {usuario.bloqueado_ate.strftime('%H:%M')}."
            )

        senha_ok = bcrypt.checkpw(
            password.encode("utf-8"), usuario.password_hash.encode("utf-8")
        )
        if not senha_ok:
            usuario.tentativas_falhas += 1
            if usuario.tentativas_falhas >= settings.LOGIN_MAX_TENTATIVAS:
                usuario.bloqueado_ate = agora + timedelta(minutes=settings.LOGIN_BLOQUEIO_MINUTOS)
                usuario.tentativas_falhas = 0
            await self.session.flush()
            raise UnauthorizedError("Usuário ou senha inválidos")

        usuario.tentativas_falhas = 0
        usuario.bloqueado_ate = None
        usuario.last_login_at = agora
        await self._sessoes.delete_expiradas()

        token = secrets.token_urlsafe(32)
        sessao = Sessao(
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            expira_em=agora + timedelta(hours=settings.SESSION_TTL_HOURS),
            ip_criacao=ip,
        )
        self.session.add(sessao)
        await self.session.flush()
        return usuario, token

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

    async def logout(self, token: Optional[str]) -> None:
        """Apaga a sessão correspondente, se existir. Nunca falha por token ausente/inválido."""
        if not token:
            return
        sessao = await self._sessoes.get_by_token_hash(_hash_token(token))
        if sessao is not None:
            await self._sessoes.delete(sessao)
