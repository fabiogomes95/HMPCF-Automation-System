from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.models.usuario import Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.recepcao_repository import RecepcaoRepository
from app.schemas.common import PaginatedResponse
from app.schemas.recepcao import (
    PacienteAgrupadoResponse,
    PlanilhaAtendimentoResponse,
    PlanilhaMensalResponse,
    RecepcaoCreate,
    RecepcaoListResponse,
    RecepcaoResponse,
    RecepcaoUpdate,
)
from app.services.auditoria_service import AuditoriaService

_INICIO_DIURNO = time(7, 0)
_INICIO_NOTURNO = time(19, 0)
_FUSO_HOSPITAL = ZoneInfo("America/Sao_Paulo")


def _turno_e_dia_referencia(dt: datetime) -> tuple[str, date]:
    """Diurno = 07:00-18:59, noturno = 19:00-06:59 (vira a virada do dia),
    sempre no horário de Brasília -- data_atendimento fica salvo em UTC, e
    classificar pela hora UTC direto dava turno errado perto da troca de
    turno (ex.: 16:24 local = 19:24 UTC, bateria como NOTURNO sem converter).
    O plantão noturno é "referenciado" pelo dia em que começou -- 03:00 de
    01/09 pertence ao noturno de 31/08, não ao diurno de 01/09."""
    local = dt.astimezone(_FUSO_HOSPITAL)
    hora = local.time()
    if _INICIO_DIURNO <= hora < _INICIO_NOTURNO:
        return "DIURNO", local.date()
    if hora >= _INICIO_NOTURNO:
        return "NOTURNO", local.date()
    return "NOTURNO", local.date() - timedelta(days=1)


def _montar_endereco(logpcn: Optional[str], numpcn: Optional[str], bairro: Optional[str]) -> Optional[str]:
    """Formato 'Rua, Número - Bairro', omitindo partes ausentes."""
    rua_num = (logpcn or "").strip()
    numero = (numpcn or "").strip()
    if numero:
        rua_num = f"{rua_num}, {numero}" if rua_num else numero
    bairro = (bairro or "").strip()
    if bairro:
        return f"{rua_num} - {bairro}" if rua_num else bairro
    return rua_num or None


# Janela de duplicata -- manter igual a JANELA_REPETIDO_MIN em frontend/src/utils.js
JANELA_REPETIDO_MIN = 15


def _chaves_paciente(a: RecepcaoAtendimento) -> set:
    """Identidade do paciente pra detectar duplicata: id do cadastro, CPF, CNS
    ou nome+nascimento (pega também cadastros duplicados da mesma pessoa)."""
    p = a.paciente
    chaves = {("id", a.paciente_id)}
    if p is not None:
        if p.num_cpf:
            chaves.add(("cpf", p.num_cpf))
        if p.cns:
            chaves.add(("cns", p.cns))
        if p.nome and p.dtnasc:
            chaves.add(("nome", p.nome.strip().upper(), p.dtnasc))
    return chaves


def _linha_planilha(a: RecepcaoAtendimento) -> PlanilhaAtendimentoResponse:
    turno, dia_referencia = _turno_e_dia_referencia(a.data_atendimento)
    p = a.paciente
    return PlanilhaAtendimentoResponse(
        atendimento_id=a.id,
        registro=a.registro,
        data_atendimento=a.data_atendimento,
        nome=p.nome if p else None,
        dtnasc=p.dtnasc if p else None,
        sexo=p.sexo if p else None,
        raca=p.raca if p else None,
        cidade=p.cidade if p else None,
        num_cpf=p.num_cpf if p else None,
        cns=p.cns if p else None,
        procedencia=a.procedencia,
        endereco=_montar_endereco(p.logpcn, p.numpcn, p.bairro_pcnte) if p else None,
        telefone=f"{p.ddtel_pcnte or ''}{p.tel_pcnte or ''}".strip() or None if p else None,
        dia_referencia=dia_referencia,
        turno=turno,
    )


class RecepcaoService:
    """
    Registra, organiza e consulta fichas de atendimento da recepção.
    Sem automação clínica — apenas armazenamento e consulta.
    """

    def __init__(self, session: AsyncSession, usuario: Optional[Usuario] = None) -> None:
        self.session = session
        self._repo = RecepcaoRepository(session)
        self._paciente_repo = PacienteRepository(session)
        self._usuario = usuario
        self._auditoria = AuditoriaService(session)

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

    async def planilha_mensal(self, ano: int, mes: int) -> PlanilhaMensalResponse:
        """Relatório mensal estilo planilha (ver docs do pedido) -- uma linha por
        atendimento, com turno (DIURNO/NOTURNO) e dia_referencia calculados.
        Busca com folga de 1 dia de cada lado pra não perder atendimentos do
        plantão noturno que viram a virada do mês, depois filtra pelo mês real."""
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
        inicio_busca = datetime.combine(inicio_mes - timedelta(days=1), time.min, tzinfo=timezone.utc)
        fim_busca = datetime.combine(fim_mes + timedelta(days=1), time.min, tzinfo=timezone.utc)

        atendimentos = await self._repo.list_por_intervalo(inicio_busca, fim_busca)

        items = []
        for a in atendimentos:
            linha = _linha_planilha(a)
            if inicio_mes <= linha.dia_referencia < fim_mes:
                items.append(linha)

        return PlanilhaMensalResponse(ano=ano, mes=mes, total=len(items), items=items)

    async def planilha_plantao(self, dia: date, turno: str) -> PlanilhaMensalResponse:
        """Só um plantão (12h) -- usado pelo refresh rápido da Planilha, que
        roda a cada poucos segundos e não pode baixar o mês inteiro.
        DIURNO = dia 07:00-19:00; NOTURNO = dia 19:00 até 07:00 do dia seguinte
        (mesma regra de _turno_e_dia_referencia)."""
        hora_inicio = _INICIO_DIURNO if turno == "DIURNO" else _INICIO_NOTURNO
        inicio = datetime.combine(dia, hora_inicio, tzinfo=_FUSO_HOSPITAL)
        atendimentos = await self._repo.list_por_intervalo(inicio, inicio + timedelta(hours=12))
        items = [_linha_planilha(a) for a in atendimentos]
        return PlanilhaMensalResponse(ano=dia.year, mes=dia.month, total=len(items), items=items)

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
        await self._auditoria.registrar(self._usuario, "criar", "atendimento", atendimento.id)
        return RecepcaoResponse.model_validate(atendimento)

    async def atualizar(
        self, atendimento_id: int, data: RecepcaoUpdate
    ) -> RecepcaoResponse:
        atendimento = await self._repo.get_by_id(atendimento_id)
        if atendimento is None:
            raise NotFoundError("Atendimento", atendimento_id)

        update_data = data.model_dump(exclude_unset=True)
        if "paciente_id" in update_data:
            novo = update_data["paciente_id"]
            if novo is None or novo == atendimento.paciente_id:
                update_data.pop("paciente_id")
            elif not await self._paciente_repo.get(novo):
                raise NotFoundError("Paciente", novo)
        for field, value in update_data.items():
            setattr(atendimento, field, value)

        atendimento.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(atendimento)

        # Recarrega com paciente após flush
        atendimento = await self._repo.get_by_id(atendimento_id)
        await self._auditoria.registrar(
            self._usuario, "atualizar", "atendimento", atendimento_id,
            campos_alterados=list(update_data.keys()),
        )
        return RecepcaoResponse.model_validate(atendimento)

    async def remover_repetido(self, atendimento_id: int) -> None:
        """Remove um atendimento SÓ se ele for duplicata (liberado pra recepção).
        Mesma regra da tela (frontend/src/utils.js idsRepetidosPorPlantao): o
        mesmo paciente foi registrado de novo, no mesmo plantão, logo em seguida
        ou em até JANELA_REPETIDO_MIN minutos -- fica o registro mais novo e sai
        este. Retorno real (horas depois) é recusado."""
        atendimento = await self._repo.get_by_id(atendimento_id)
        if atendimento is None:
            raise NotFoundError("Atendimento", atendimento_id)

        turno, dia = _turno_e_dia_referencia(atendimento.data_atendimento)
        hora_inicio = _INICIO_DIURNO if turno == "DIURNO" else _INICIO_NOTURNO
        inicio = datetime.combine(dia, hora_inicio, tzinfo=_FUSO_HOSPITAL)
        plantao = await self._repo.list_por_intervalo(inicio, inicio + timedelta(hours=12))

        idx = next((i for i, a in enumerate(plantao) if a.id == atendimento_id), None)
        chaves = _chaves_paciente(atendimento)
        seguintes = plantao[idx + 1:] if idx is not None else []
        limite = atendimento.data_atendimento + timedelta(minutes=JANELA_REPETIDO_MIN)
        eh_repetido = any(
            chaves & _chaves_paciente(b) and (pos == 0 or b.data_atendimento <= limite)
            for pos, b in enumerate(seguintes)
        )
        if not eh_repetido:
            raise BusinessRuleError(
                "Este atendimento não é repetido (não há registro do mesmo paciente logo "
                f"em seguida nem em até {JANELA_REPETIDO_MIN} min no mesmo plantão)"
            )
        await self.remover(atendimento_id)

    async def remover(self, atendimento_id: int) -> None:
        atendimento = await self._repo.get_by_id(atendimento_id)
        if atendimento is None:
            raise NotFoundError("Atendimento", atendimento_id)
        await self._repo.delete(atendimento)
        await self._auditoria.registrar(self._usuario, "remover", "atendimento", atendimento_id)
