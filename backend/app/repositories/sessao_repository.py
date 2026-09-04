from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select

from app.models.sessao import Sessao
from app.repositories.base import BaseRepository


class SessaoRepository(BaseRepository[Sessao]):
    model = Sessao

    async def get_by_token_hash(self, token_hash: str) -> Optional[Sessao]:
        """Busca a sessão pelo hash do token; `usuario` já vem carregado (lazy='joined')."""
        stmt = select(Sessao).where(Sessao.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_expiradas(self) -> None:
        """Limpeza oportunista — chamada a cada login, sem job/cron dedicado."""
        stmt = delete(Sessao).where(Sessao.expira_em < datetime.now(timezone.utc))
        await self.session.execute(stmt)
        await self.session.flush()
