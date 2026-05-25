from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.recepcao_repository import RecepcaoRepository
from app.schemas.common import PaginatedResponse
from app.schemas.recepcao import (
    PacienteAgrupadoResponse,
    RecepcaoCreate,
    RecepcaoListResponse,
    RecepcaoResponse,
    RecepcaoUpdate,
)


class RecepcaoService:
    """
    Registra, organiza e consulta fichas de atendimento da recepção.
    Sem automação clínica — apenas armazenamento e consulta.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._repo = RecepcaoRepository(session)
        self._paciente_repo = PacienteRepository(session)

    # ── Consultas ──────────────────────────────────────────────────────────────

    async def listar(
        self,
        page: int,
        page_size: int,
        q: Optional[str] = None,
    ) -> PaginatedResponse[RecepcaoListResponse]:
        """Lista atendimentos com busca opcional por nome/CPF do paciente."""
        offset = (page - 1) * page_size
        if q and q.strip():
            items = await self._repo.list_by_query(q.strip(), limit=page_size, offset=offset)
            total = await self._repo.count_by_query(q.strip())
        else:
            items = await self._repo.list_recent(limit=page_size, offset=offset)
            total = await self._repo.count_all()
        pages = max(1, (total + page_size - 1) // page_size)
        return PaginatedResponse(
            items=[RecepcaoListResponse.model_validate(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def listar_recentes(
        self,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[RecepcaoListResponse]:
        offset = (page - 1) * page_size
        items = await self._repo.list_recent(limit=page_size, offset=offset)
        total = await self._repo.count_all()
        pages = max(1, (total + page_size - 1) // page_size)
        return PaginatedResponse(
            items=[RecepcaoListResponse.model_validate(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def obter(self, atendimento_id: int) -> RecepcaoResponse:
        atendimento = await self._repo.get_by_id(atendimento_id)
        if atendimento is None:
            raise NotFoundError("Atendimento", atendimento_id)
        return RecepcaoResponse.model_validate(atendimento)

    async def listar_por_paciente(
        self,
        paciente_id: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[RecepcaoListResponse]:
        if not await self._paciente_repo.get(paciente_id):
            raise NotFoundError("Paciente", paciente_id)
        offset = (page - 1) * page_size
        items = await self._repo.list_by_paciente(paciente_id, limit=page_size, offset=offset)
        total = await self._repo.count_by_paciente(paciente_id)
        pages = max(1, (total + page_size - 1) // page_size)
        return PaginatedResponse(
            items=[RecepcaoListResponse.model_validate(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def listar_agrupado(
        self,
        page: int,
        page_size: int,
        q: Optional[str] = None,
    ) -> PaginatedResponse[PacienteAgrupadoResponse]:
        """Busca pacientes únicos agrupados com total de entradas e última data."""
        offset = (page - 1) * page_size
        if q and q.strip():
            rows = await self._repo.search_grouped_by_patient(q.strip(), limit=page_size, offset=offset)
            total = await self._repo.count_grouped_by_patient(q.strip())
        else:
            rows = []
            total = 0

        items = []
        for row in rows:
            items.append(PacienteAgrupadoResponse(
                paciente_id=row.paciente_id,
                nome=row.nome,
                num_cpf=row.num_cpf,
                cns=row.cns,
                dtnasc=row.dtnasc,
                total_entradas=row.total_entradas,
                ultima_data=row.ultima_data,
            ))

        pages = max(1, (total + page_size - 1) // page_size)
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ── Escrita ────────────────────────────────────────────────────────────────

    async def criar(self, data: RecepcaoCreate) -> RecepcaoResponse:
        """Valida paciente e registra atendimento."""
        if not await self._paciente_repo.get(data.paciente_id):
            raise NotFoundError("Paciente", data.paciente_id)

        dump = data.model_dump()
        if dump.get("data_atendimento") is None:
            dump["data_atendimento"] = datetime.now(timezone.utc)

        atendimento = RecepcaoAtendimento(**dump)
        atendimento = await self._repo.add_and_load(atendimento)
        return RecepcaoResponse.model_validate(atendimento)

    async def atualizar(
        self, atendimento_id: int, data: RecepcaoUpdate
    ) -> RecepcaoResponse:
        atendimento = await self._repo.get_by_id(atendimento_id)
        if atendimento is None:
            raise NotFoundError("Atendimento", atendimento_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(atendimento, field, value)

        atendimento.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(atendimento)

        # Recarrega com paciente após flush
        atendimento = await self._repo.get_by_id(atendimento_id)
        return RecepcaoResponse.model_validate(atendimento)

    async def remover(self, atendimento_id: int) -> None:
        atendimento = await self._repo.get(atendimento_id)
        if atendimento is None:
            raise NotFoundError("Atendimento", atendimento_id)
        await self._repo.delete(atendimento)
