"""
RECEPCAO.PY — Endpoints REST do módulo de recepção.

ENDPOINTS:
  GET    /api/v1/recepcao/pacientes        → Listar pacientes (com busca)
  GET    /api/v1/recepcao/pacientes/{cpf}  → Buscar paciente por CPF
  POST   /api/v1/recepcao/pacientes        → Criar paciente
  PUT    /api/v1/recepcao/pacientes/{cpf}  → Atualizar paciente
  DELETE /api/v1/recepcao/pacientes/{cpf}  → Deletar paciente
  GET    /api/v1/recepcao/atendimentos     → Listar atendimentos
  GET    /api/v1/recepcao/estatisticas     → Totais (dashboard)

PADRÃO: ROTA → SERVICE
  Cada endpoint chama a função correspondente em service.py.
  O endpoint é responsável apenas por:
    1. Extrair parâmetros da requisição
    2. Chamar o service
    3. Retornar a resposta HTTP

  A lógica em si fica no service — testável sem HTTP.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.modules.recepcao import service as recepcao_service
from app.modules.recepcao.schemas import (
    AtendimentoCreate,
    AtendimentoResponse,
    PacienteCreate,
    PacienteResponse,
    PacienteUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/recepcao", tags=["recepcao"])


# ── PACIENTES ─────────────────────────────────────────────────


@router.get("/pacientes")
async def listar_pacientes(
    nome: str = Query(None, description="Filtrar por nome"),
    cpf: str = Query(None, description="Filtrar por CPF"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
) -> PaginatedResponse:
    """Lista pacientes com paginação e filtros opcionais."""
    return recepcao_service.listar_pacientes(
        nome=nome, cpf=cpf, pagina=pagina, por_pagina=por_pagina
    )


@router.get("/pacientes/duplicata")
async def verificar_duplicata(
    nome: str = Query(...),
    dn: str = Query(...),
) -> Optional[dict]:
    return recepcao_service.buscar_duplicata(nome, dn)


@router.get("/pacientes/{cpf}")
async def buscar_paciente(cpf: str) -> PacienteResponse:
    """Busca um paciente pelo CPF."""
    result = recepcao_service.buscar_paciente(cpf)
    if not result:
        raise HTTPException(status_code=404, detail="Paciente nao encontrado")
    return result


@router.post("/pacientes", status_code=201)
async def criar_paciente(dados: PacienteCreate) -> PacienteResponse:
    """Cadastra um novo paciente."""
    existente = recepcao_service.buscar_paciente(dados.cpf)
    if existente:
        raise HTTPException(status_code=409, detail="CPF ja cadastrado")
    return recepcao_service.criar_paciente(dados.model_dump(exclude_unset=True, by_alias=True))


@router.put("/pacientes/{cpf}")
async def atualizar_paciente(cpf: str, dados: PacienteUpdate) -> PacienteResponse:
    """Atualiza dados de um paciente existente."""
    existente = recepcao_service.buscar_paciente(cpf)
    if not existente:
        raise HTTPException(status_code=404, detail="Paciente nao encontrado")
    atualizado = recepcao_service.atualizar_paciente(
        cpf, dados.model_dump(exclude_unset=True, by_alias=True)
    )
    return atualizado or existente


@router.delete("/pacientes/{cpf}", status_code=204)
async def deletar_paciente(cpf: str) -> None:
    """Remove um paciente do cadastro."""
    removido = recepcao_service.deletar_paciente(cpf)
    if not removido:
        raise HTTPException(status_code=404, detail="Paciente nao encontrado")


# ── ATENDIMENTOS ──────────────────────────────────────────────


@router.get("/atendimentos")
async def listar_atendimentos(
    cpf: str = Query(None, description="Filtrar por CPF do paciente"),
    data_inicio: str = Query(None, description="Data inicial (DD/MM/AAAA ou YYYY-MM-DD)"),
    data_fim: str = Query(None, description="Data final (DD/MM/AAAA ou YYYY-MM-DD)"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
) -> PaginatedResponse:
    """Lista atendimentos com filtros e paginação."""
    return recepcao_service.listar_atendimentos(
        cpf=cpf,
        data_inicio=data_inicio,
        data_fim=data_fim,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.post("/atendimentos", status_code=201)
async def criar_atendimento(dados: AtendimentoCreate) -> dict:
    payload = dados.model_dump(exclude_unset=True, exclude_none=True)
    if not payload.get("cpf"):
        raise HTTPException(status_code=422, detail="CPF é obrigatório")
    return recepcao_service.criar_atendimento(payload)


# ── ESTATÍSTICAS ─────────────────────────────────────────────


@router.get("/estatisticas")
async def estatisticas() -> dict:
    """Retorna totais do sistema (para o dashboard)."""
    return {
        "total_pacientes": recepcao_service.contar_pacientes(),
        "total_atendimentos": recepcao_service.contar_atendimentos(),
    }
