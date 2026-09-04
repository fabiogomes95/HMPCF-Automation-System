from typing import Optional

from sqlalchemy import select

from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    model = Usuario

    async def get_by_username(self, username: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
