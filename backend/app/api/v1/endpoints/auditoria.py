from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from app.api.deps import TIUser, DBSession
from app.models.log_auditoria import LogAuditoria
from app.repositories.log_auditoria_repository import LogAuditoriaRepository
from app.schemas.common import PaginatedResponse
from app.schemas.log_auditoria import LogAuditoriaResponse

router = APIRouter()

_FUSO = ZoneInfo("America/Sao_Paulo")


@router.get("/", response_model=PaginatedResponse[LogAuditoriaResponse])
async def listar_auditoria(
    session: DBSession,
    usuario: TIUser,
    recurso: Optional[str] = Query(None, description="Filtra por 'paciente' ou 'atendimento'"),
    recurso_id: Optional[int] = Query(None),
    acao: Optional[str] = Query(None, description="Filtra por 'criar', 'atualizar' ou 'remover'"),
    usuario_username: Optional[str] = Query(None, description="Parte do login de quem fez"),
    desde: Optional[date] = Query(None, description="Data inicial (inclusive), horário de Brasília"),
    ate: Optional[date] = Query(None, description="Data final (inclusive), horário de Brasília"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[LogAuditoriaResponse]:
    repo = LogAuditoriaRepository(session)
    filtros = []
    if recurso:
        filtros.append(LogAuditoria.recurso == recurso)
    if recurso_id is not None:
        filtros.append(LogAuditoria.recurso_id == recurso_id)
    if acao:
        filtros.append(LogAuditoria.acao == acao)
    if usuario_username and usuario_username.strip():
        filtros.append(LogAuditoria.usuario_username.ilike(f"%{usuario_username.strip()}%"))
    if desde:
        filtros.append(LogAuditoria.criado_em >= datetime.combine(desde, time.min, tzinfo=_FUSO))
    if ate:
        filtros.append(LogAuditoria.criado_em < datetime.combine(ate + timedelta(days=1), time.min, tzinfo=_FUSO))

    offset = (page - 1) * page_size
    items = await repo.list(
        *filtros, limit=page_size, offset=offset, order_by=LogAuditoria.criado_em.desc()
    )
    total = await repo.count(*filtros)
    pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        items=[LogAuditoriaResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
