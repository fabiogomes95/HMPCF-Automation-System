"""Rotas do BPA local — finas, só leem a requisição e chamam os services.
Mesmas URLs e respostas do antigo app Flask (a página atual depende delas).

Funções `def` (não async): Firebird e psycopg2 bloqueiam, então o FastAPI
roda cada chamada numa thread separada."""
from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from bpa_local import postgres
from bpa_local.cache import cache
from bpa_local.services import digitacao, geracao, migracao, producao

router = APIRouter(prefix="/api")

Corpo = Optional[dict]


def _corpo(d: Corpo) -> dict:
    return d or {}


# ── Digitação ─────────────────────────────────────────────────────────────────
@router.get("/buscar")
def buscar(q: str = "", incluir_sus: str = "1"):
    return digitacao.buscar(q, incluir_sus != "0")


@router.post("/cabecalho")
def cabecalho(d: Corpo = Body(None)):
    return digitacao.cabecalho(_corpo(d))


@router.post("/gravar")
def gravar(d: Corpo = Body(None)):
    return digitacao.gravar(_corpo(d))


@router.post("/recarregar")
def recarregar():
    return digitacao.recarregar()


@router.get("/prontuario/buscar")
def prontuario_buscar(q: str = ""):
    return digitacao.prontuario_buscar(q)


@router.post("/enfermeiros/dividir")
def enfermeiros_dividir(d: Corpo = Body(None)):
    return digitacao.enfermeiros_dividir(_corpo(d))


@router.get("/lotes")
def lotes():
    return digitacao.lotes()


@router.get("/lote")
def lote(arquivo: str = ""):
    return digitacao.lote(arquivo)


@router.get("/profissionais")
def profissionais():
    return cache.profissionais


@router.get("/competencias")
def competencias():
    return postgres.competencias_disponiveis()


# ── Produção (Firebird S_PRD / CADCNS) ────────────────────────────────────────
@router.get("/conferencia")
def conferencia(data_ini: str = "", data_fim: str = ""):
    return producao.conferir(data_ini, data_fim)


@router.post("/pacientes/completar")
def pacientes_completar(d: Corpo = Body(None)):
    return producao.completar_paciente(_corpo(d))


@router.post("/conferencia/reenviar")
def conferencia_reenviar(d: Corpo = Body(None)):
    return producao.reenviar_faltantes(_corpo(d))


@router.get("/fechamento")
def fechamento(competencia: str = ""):
    return producao.fechamento(competencia)


# ── Geração do BPA-I ──────────────────────────────────────────────────────────
@router.post("/gerar")
def gerar(d: Corpo = Body(None)):
    return geracao.gerar(_corpo(d))


# ── Migração Postgres → Firebird ──────────────────────────────────────────────
@router.post("/migracao/preview")
def migracao_preview(d: Corpo = Body(None)):
    return migracao.preview(_corpo(d))


@router.get("/migracao/stream")
def migracao_stream(mes: str = ""):
    return StreamingResponse(
        migracao.stream(mes or migracao.mes_padrao()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
