"""Aba Entradas (faturamento e TI): em que dias o paciente deu entrada, no
sistema e/ou nas planilhas manuais — ver app/services/entradas_service.py."""
from fastapi import APIRouter, Query

from app.api.deps import DBSession, FaturamentoUser
from app.services import entradas_service
from app.services.entradas_service import Fonte

router = APIRouter()


@router.get("")
async def buscar_entradas(
    session: DBSession,
    _: FaturamentoUser,
    q: str = Query(..., description="CPF, SUS ou nome"),
    fonte: Fonte = Query("ambos"),
) -> dict:
    return await entradas_service.buscar(session, q, fonte)


@router.get("/planilhas")
async def resumo_planilhas(session: DBSession, _: FaturamentoUser) -> dict:
    """Quantas entradas das planilhas estão carregadas, de quando a quando."""
    return await entradas_service.resumo_planilhas(session)
