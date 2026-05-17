"""
BPA.PY — Endpoints do Boletim de Produção Ambulatorial.

O BPA é um relatório do SUS que lista todos os procedimentos
ambulatoriais realizados em um período.

ESTE ARQUIVO É UM PLACEHOLDER (Fase 1).
A implementação real virá quando migrarmos o módulo
legado de integracao/exportar_bpa.py para este novo formato.

ESTRUTURA FUTURA:
  GET  /api/v1/bpa/                  → Listar BPA gerados
  POST /api/v1/bpa/gerar             → Gerar novo BPA
  GET  /api/v1/bpa/{id}              → Download de um BPA específico
  POST /api/v1/bpa/exportar          → Exportar para formato do SUS
"""

from __future__ import annotations

from fastapi import APIRouter

# prefix="/bpa" → todas as rotas deste arquivo começam com /bpa
# tags=["bpa"]  → agrupa no Swagger (/docs)
router = APIRouter(prefix="/bpa", tags=["bpa"])


@router.get("/")
async def list_bpa() -> dict[str, str]:
    """
    Placeholder — listar BPA.

    Futuramente vai retornar lista de BPA gerados com:
      - Período
      - Total de procedimentos
      - Status (rascunho, finalizado, enviado)
      - Data de criação
    """
    return {
        "message": "Módulo BPA — ainda não implementado",
        "hint": "Endpoint reservado para a migração do módulo BPA",
    }
