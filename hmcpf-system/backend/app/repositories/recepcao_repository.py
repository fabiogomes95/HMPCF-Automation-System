from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.repositories.base import BaseRepository


class RecepcaoRepository(BaseRepository[RecepcaoAtendimento]):
    model = RecepcaoAtendimento

    # ── Consultas com paciente embutido ────────────────────────────────────────

    async def get_by_id(self, id: int) -> Optional[RecepcaoAtendimento]:
        """Busca por ID com dados do paciente carregados.
        populate_existing=True força releitura mesmo quando o objeto já está no identity map."""
        stmt = (
            select(RecepcaoAtendimento)
            .options(selectinload(RecepcaoAtendimento.paciente))
            .where(RecepcaoAtendimento.id == id)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int, offset: int) -> list[RecepcaoAtendimento]:
        """Lista atendimentos mais recentes primeiro."""
        stmt = (
            select(RecepcaoAtendimento)
            .options(selectinload(RecepcaoAtendimento.paciente))
            .order_by(RecepcaoAtendimento.data_atendimento.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(RecepcaoAtendimento)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_paciente(
        self, paciente_id: int, limit: int, offset: int
    ) -> list[RecepcaoAtendimento]:
        """Todos os atendimentos de um paciente específico."""
        stmt = (
            select(RecepcaoAtendimento)
            .options(selectinload(RecepcaoAtendimento.paciente))
            .where(RecepcaoAtendimento.paciente_id == paciente_id)
            .order_by(RecepcaoAtendimento.data_atendimento.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_paciente(self, paciente_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(RecepcaoAtendimento)
            .where(RecepcaoAtendimento.paciente_id == paciente_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add_and_load(self, obj: RecepcaoAtendimento) -> RecepcaoAtendimento:
        """Persiste e recarrega com o relacionamento paciente."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return await self.get_by_id(obj.id)  # type: ignore[return-value]
