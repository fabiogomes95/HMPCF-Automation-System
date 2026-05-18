"""
REPORTS.PY — Endpoints de relatórios gerenciais.

Aqui ficarão os endpoints para gerar relatórios em PDF/Excel:
  - Relatório mensal de produção
  - Relatório de auditoria
  - Dashboard de indicadores
  - Relatório comparativo mensal

ESTE ARQUIVO É UM PLACEHOLDER (Fase 1).
A implementação real usará:
  - fpdf2 (já existente no projeto legado) para PDF
  - openpyxl para Excel
  - matplotlib/seaborn para gráficos

ESTRUTURA FUTURA:
  GET  /api/v1/reports/               → Listar relatórios disponíveis
  POST /api/v1/reports/gerar          → Gerar relatório sob demanda
  GET  /api/v1/reports/{tipo}/download → Download do arquivo gerado
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/")
async def list_reports() -> dict[str, str]:
    """
    Placeholder — listar relatórios disponíveis.

    Futuramente vai retornar os tipos de relatório disponíveis:
      - "mensal" → Resumo mensal de produção
      - "auditoria" → Auditoria de atendimentos
      - "comparativo" → Comparativo entre meses
      - "indicadores" → Dashboard com indicadores
    """
    return {
        "message": "Módulo de Relatórios — ainda não implementado",
        "hint": "Endpoint reservado para a migração dos relatórios",
    }
