from typing import Optional

from sqlalchemy import func, or_, select

from app.models.paciente import Paciente
from app.repositories.base import BaseRepository


class PacienteRepository(BaseRepository[Paciente]):
    model = Paciente

    async def get_by_cpf(self, cpf: str) -> Optional[Paciente]:
        stmt = select(Paciente).where(Paciente.num_cpf == cpf)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_cns(self, cns: str) -> Optional[Paciente]:
        stmt = select(Paciente).where(Paciente.cns == cns)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_documento(self, documento: str) -> Optional[Paciente]:
        """Busca por CPF ou CNS exato."""
        stmt = select(Paciente).where(
            or_(Paciente.num_cpf == documento, Paciente.cns == documento)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, q: str, limit: int, offset: int) -> list[Paciente]:
        """Busca textual em nome (case-insensitive), CPF e CNS."""
        termo = f"%{q.upper()}%"
        stmt = (
            select(Paciente)
            .where(
                or_(
                    func.upper(Paciente.nome).like(termo),
                    Paciente.num_cpf.like(f"%{q}%"),
                    Paciente.cns.like(f"%{q}%"),
                )
            )
            .order_by(Paciente.nome)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_search(self, q: str) -> int:
        termo = f"%{q.upper()}%"
        stmt = select(func.count()).select_from(Paciente).where(
            or_(
                func.upper(Paciente.nome).like(termo),
                Paciente.num_cpf.like(f"%{q}%"),
                Paciente.cns.like(f"%{q}%"),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
