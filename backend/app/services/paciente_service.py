import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.paciente import Paciente
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.common import PaginatedResponse
from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate


class PacienteService:
    """
    Regras de negócio do módulo Pacientes.
    Recebe a sessão assíncrona e delega queries ao PacienteRepository.
    Nunca lança HTTPException — apenas exceções de domínio (HMPCFError).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._repo = PacienteRepository(session)

    # ── Leitura ────────────────────────────────────────────────────────────────

    async def listar(
        self,
        q: Optional[str],
        page: int,
        page_size: int,
    ) -> PaginatedResponse[PacienteResponse]:
        offset = (page - 1) * page_size
        if q:
            items = await self._repo.search(q, limit=page_size, offset=offset)
            total = await self._repo.count_search(q)
        else:
            items = await self._repo.list(
                limit=page_size,
                offset=offset,
                order_by=Paciente.nome,
            )
            total = await self._repo.count()

        pages = max(1, (total + page_size - 1) // page_size)
        return PaginatedResponse(
            items=[PacienteResponse.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def obter(self, paciente_id: int) -> PacienteResponse:
        paciente = await self._repo.get(paciente_id)
        if paciente is None:
            raise NotFoundError("Paciente", paciente_id)
        return PacienteResponse.model_validate(paciente)

    async def buscar_por_documento(self, documento: str) -> PacienteResponse:
        """Busca por CPF ou CNS — retorna 404 se não encontrado."""
        doc = re.sub(r"\D", "", documento)
        if not doc:
            raise NotFoundError("Paciente", documento)
        paciente = await self._repo.get_by_documento(doc)
        if paciente is None:
            raise NotFoundError("Paciente", documento)
        return PacienteResponse.model_validate(paciente)

    # ── Escrita ────────────────────────────────────────────────────────────────

    async def criar(self, data: PacienteCreate) -> PacienteResponse:
        """Cria paciente verificando unicidade de CPF e CNS."""
        if data.num_cpf:
            if await self._repo.get_by_cpf(data.num_cpf):
                raise ConflictError(f"Paciente com CPF {data.num_cpf} já existe")
        if data.cns:
            if await self._repo.get_by_cns(data.cns):
                raise ConflictError(f"Paciente com CNS {data.cns} já existe")

        paciente = Paciente(**data.model_dump())
        paciente = await self._repo.add(paciente)
        return PacienteResponse.model_validate(paciente)

    async def atualizar(self, paciente_id: int, data: PacienteUpdate) -> PacienteResponse:
        """Atualiza apenas os campos enviados (semântica PATCH)."""
        paciente = await self._repo.get(paciente_id)
        if paciente is None:
            raise NotFoundError("Paciente", paciente_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(paciente, field, value)

        await self.session.flush()
        await self.session.refresh(paciente)
        return PacienteResponse.model_validate(paciente)

    async def remover(self, paciente_id: int) -> None:
        paciente = await self._repo.get(paciente_id)
        if paciente is None:
            raise NotFoundError("Paciente", paciente_id)
        await self._repo.delete(paciente)
