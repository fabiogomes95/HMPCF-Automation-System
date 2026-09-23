import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.recepcao_repository import RecepcaoRepository
from app.schemas.common import PaginatedResponse
from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate
from app.services.auditoria_service import AuditoriaService


class PacienteService:
    """
    Regras de negócio do módulo Pacientes.
    Recebe a sessão assíncrona e delega queries ao PacienteRepository.
    Nunca lança HTTPException — apenas exceções de domínio (HMPCFError).
    """

    def __init__(self, session: AsyncSession, usuario: Optional[Usuario] = None) -> None:
        self.session = session
        self._repo = PacienteRepository(session)
        self._usuario = usuario
        self._auditoria = AuditoriaService(session)

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

        # Só o CPF importa pra essa marcação -- sinaliza sem_documento sozinho
        # quando a recepção deixa o CPF em branco, sem precisar de nada na tela
        # (usado futuramente na exportação BPA/Firebird).
        paciente = Paciente(**data.model_dump(), sem_documento=not data.num_cpf)
        paciente = await self._repo.add(paciente)
        await self._auditoria.registrar(self._usuario, "criar", "paciente", paciente.id)
        return PacienteResponse.model_validate(paciente)

    async def atualizar(self, paciente_id: int, data: PacienteUpdate) -> PacienteResponse:
        """Atualiza apenas os campos enviados (semântica PATCH)."""
        paciente = await self._repo.get(paciente_id)
        if paciente is None:
            raise NotFoundError("Paciente", paciente_id)

        update_data = data.model_dump(exclude_unset=True)

        # Documento vazio no form nunca apaga o que já está salvo -- só completa
        # ou troca. sem_documento é derivado do CPF, não aceito do cliente.
        update_data.pop("sem_documento", None)
        for doc in ("num_cpf", "cns"):
            if not update_data.get(doc) or update_data[doc] == getattr(paciente, doc):
                update_data.pop(doc, None)

        novo_cpf = update_data.get("num_cpf")
        if novo_cpf:
            outro = await self._repo.get_by_cpf(novo_cpf)
            if outro is not None and outro.id != paciente_id:
                raise ConflictError(
                    f"CPF {novo_cpf} já pertence a outro paciente ({outro.nome}, id {outro.id})"
                )

        # SUS é só complemento: se já pertence a outro cadastro, mantém o SUS
        # atual em vez de travar o atendimento.
        novo_cns = update_data.get("cns")
        if novo_cns:
            outro = await self._repo.get_by_cns(novo_cns)
            if outro is not None and outro.id != paciente_id:
                update_data.pop("cns")

        for field, value in update_data.items():
            setattr(paciente, field, value)
        if novo_cpf:
            paciente.sem_documento = False

        await self.session.flush()
        await self.session.refresh(paciente)
        await self._auditoria.registrar(
            self._usuario, "atualizar", "paciente", paciente_id,
            campos_alterados=list(update_data.keys()),
        )
        return PacienteResponse.model_validate(paciente)

    async def remover(self, paciente_id: int) -> None:
        paciente = await self._repo.get(paciente_id)
        if paciente is None:
            raise NotFoundError("Paciente", paciente_id)
        if await RecepcaoRepository(self.session).count_by_paciente(paciente_id):
            raise BusinessRuleError("Paciente tem atendimentos -- mova ou exclua os atendimentos antes")
        await self._repo.delete(paciente)
        await self._auditoria.registrar(self._usuario, "remover", "paciente", paciente_id)
