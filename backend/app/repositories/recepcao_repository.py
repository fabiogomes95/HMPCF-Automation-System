from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.paciente import Paciente
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

    async def list_by_query(
        self, q: str, limit: int, offset: int
    ) -> list[RecepcaoAtendimento]:
        """Busca atendimentos filtrando por nome ou CPF do paciente."""
        term = f"%{q}%"
        stmt = (
            select(RecepcaoAtendimento)
            .join(RecepcaoAtendimento.paciente)
            .options(selectinload(RecepcaoAtendimento.paciente))
            .where(
                or_(
                    Paciente.num_cpf.ilike(term),
                    Paciente.nome.ilike(term),
                    Paciente.cns.ilike(term),
                )
            )
            .order_by(RecepcaoAtendimento.data_atendimento.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_query(self, q: str) -> int:
        term = f"%{q}%"
        stmt = (
            select(func.count())
            .select_from(RecepcaoAtendimento)
            .join(RecepcaoAtendimento.paciente)
            .where(
                or_(
                    Paciente.num_cpf.ilike(term),
                    Paciente.nome.ilike(term),
                    Paciente.cns.ilike(term),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def search_grouped_by_patient(
        self, q: str, limit: int, offset: int
    ) -> list[tuple]:
        """
        Retorna pacientes únicos com total de entradas e última data.
        Cada tupla: (paciente_id, nome, num_cpf, cns, dtnasc, total_entradas, ultima_data)
        """
        term = f"%{q}%"
        stmt = (
            select(
                RecepcaoAtendimento.paciente_id,
                Paciente.nome,
                Paciente.num_cpf,
                Paciente.cns,
                Paciente.dtnasc,
                func.count(RecepcaoAtendimento.id).label("total_entradas"),
                func.max(RecepcaoAtendimento.data_atendimento).label("ultima_data"),
            )
            .join(RecepcaoAtendimento.paciente)
            .where(
                or_(
                    Paciente.num_cpf.ilike(term),
                    Paciente.nome.ilike(term),
                    Paciente.cns.ilike(term),
                )
            )
            .group_by(
                RecepcaoAtendimento.paciente_id,
                Paciente.nome,
                Paciente.num_cpf,
                Paciente.cns,
                Paciente.dtnasc,
            )
            .order_by(func.max(RecepcaoAtendimento.data_atendimento).desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.all())


    async def count_grouped_by_patient(self, q: str) -> int:
        """Conta pacientes únicos que atendem ao filtro de busca."""
        term = f"%{q}%"
        subq = (
            select(RecepcaoAtendimento.paciente_id)
            .join(RecepcaoAtendimento.paciente)
            .where(
                or_(
                    Paciente.num_cpf.ilike(term),
                    Paciente.nome.ilike(term),
                    Paciente.cns.ilike(term),
                )
            )
            .group_by(RecepcaoAtendimento.paciente_id)
            .subquery()
        )
        stmt = select(func.count()).select_from(subq)
        result = await self.session.execute(stmt)
        return result.scalar_one()


    async def add_and_load(self, obj: RecepcaoAtendimento) -> RecepcaoAtendimento:
        """Persiste e recarrega com o relacionamento paciente."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return await self.get_by_id(obj.id)  # type: ignore[return-value]
