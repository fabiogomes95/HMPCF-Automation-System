from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db

# Tipo anotado para injeção de sessão nos endpoints.
# Uso: async def endpoint(session: DBSession) -> ...
DBSession = Annotated[AsyncSession, Depends(get_db)]
