"""
MAIN.PY — Ponto de entrada do servidor FastAPI.

ESTE ARQUIVO FAZ:
  1. Configura logging (setup_logging)
  2. Cria a aplicação FastAPI
  3. Configura CORS (segurança de requisições cross-origin)
  4. Registra todas as rotas da API
  5. Fornece entrypoint para: python -m app.main

COMO RODAR:
  # Desenvolvimento (com hot-reload):
  uvicorn app.main:app --reload

  # Produção:
  uvicorn app.main:app --host 0.0.0.0 --port 8000

  # Ou diretamente pelo Python:
  python -m app.main

ACESSANDO A DOCUMENTAÇÃO:
  - Swagger UI: http://localhost:8000/docs
  - ReDoc:      http://localhost:8000/redoc

ORDEM DE INICIALIZAÇÃO:
  1. Configura logging
  2. Cria app FastAPI
  3. Adiciona middleware CORS
  4. Registra routers (health → bpa → reports → ...)
  5. Aguarda requisições
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import bpa, health, recepcao, reports
from app.core.config import settings
from app.core.logging import setup_logging

# ── Configura logging ANTES de qualquer outra coisa ────────
# Se algo der errado na inicialização, queremos ver o erro
setup_logging()

# ── Criação da aplicação FastAPI ────────────────────────────
# docs_url e redoc_url geram documentação interativa automática
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (Cross-Origin Resource Sharing) ────────────────────
# Permite que o frontend (React em localhost:5173) e o Tauri
# chamem a API sem serem bloqueados pelo navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Lista de origens permitidas
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Qualquer header HTTP
)

# ── Registro das rotas ──────────────────────────────────────
# Cada include_router adiciona um grupo de endpoints
# O prefixo /api/v1 é aplicado a TODAS as rotas
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(bpa.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(recepcao.router, prefix=settings.API_V1_PREFIX)

# ── Entrypoint direto ───────────────────────────────────────
# Permite executar com: python -m app.main
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,  # Hot-reload apenas em desenvolvimento
        log_level=settings.LOG_LEVEL.lower(),
    )
