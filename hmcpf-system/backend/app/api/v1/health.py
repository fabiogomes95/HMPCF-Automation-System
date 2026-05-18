"""
HEALTH.PY — Endpoint de healthcheck.

Healthcheck é um endpoint que MONITORES (Prometheus, UptimeRobot, etc.)
usam para saber se o servidor está vivo.

Uso: GET /api/v1/health
Resposta: {"status": "ok", "service": "HMPCF API", "version": "2.0.0"}

Num sistema enterprise, este endpoint também verifica:
  ✅ Banco de dados está acessível?
  ✅ Disco tem espaço suficiente?
  ✅ Dependências externas estão no ar?
"""

from __future__ import annotations

from fastapi import APIRouter

# APIRouter = grupo de rotas relacionadas
# Podemos adicionar tags para organização no Swagger (/docs)
router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    """
    Retorna o status atual do servidor.

    FastAPI automaticamente:
      - Converte dict → JSON
      - Retorna HTTP 200
      - Documenta no Swagger (/docs)
    """
    return {
        "status": "ok",
        "service": "HMPCF API",
        "version": "2.0.0",
    }
