"""
CONFIG.PY — Configuração centralizada do sistema.

COMO FUNCIONA:
  Usamos a biblioteca pydantic-settings para ler configurações
  de variáveis de ambiente ou do arquivo .env automaticamente.

  Vantagens:
    1. Toda config num lugar só (não espalhada pelo código)
    2. Tipagem forte (Python sabe se é str, int, bool)
    3. Fallback para valores padrão
    4. Fácil de mudar entre ambientes (dev, produção)

  Exemplo: se DEBUG=true no .env, o servidor roda com hot-reload.
           Se DEBUG=false (produção), roda sem reload e com otimizações.

PADRÃO SINGLETON:
  A variável "settings" no final do arquivo é importada por qualquer
  módulo que precise de configuração. Só existe UMA instância.
"""

from __future__ import annotations

import os
from pathlib import Path

# pydantic-settings lê automaticamente de arquivo .env
# Diferente de os.getenv() que exige chamada manual
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings — herda de BaseSettings do pydantic.

    Cada atributo é uma configuração que pode vir de:
      1. .env (arquivo)
      2. Variável de ambiente do sistema
      3. Valor padrão (default)

    A ordem de precedência: 2 > 1 > 3
    """

    # --- CONFIGURAÇÃO DO pydantic-settings ---
    # env_file: qual arquivo .env ler
    # extra="ignore": ignorar variáveis extras sem erro
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Geral ──────────────────────────────────────────────
    APP_NAME: str = "HMPCF System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False           # True = hot-reload ativado
    API_V1_PREFIX: str = "/api/v1"  # Todas as rotas começam com isso

    # ── Servidor ────────────────────────────────────────────
    HOST: str = "127.0.0.1"       # Apenas localhost (segurança)
    PORT: int = 8000
    # CORS = quais origens podem chamar a API (frontend, Tauri)
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",    # Vite dev server
        "tauri://localhost",        # Tauri desktop
    ]

    # ── Banco de Dados ──────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/hmpcf.db"
    SQLITE_TIMEOUT: int = 5       # segundos

    # ── Logging ─────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    )

    # ── Paths do Sistema ────────────────────────────────────
    # BASE_DIR = raiz do backend (app/)
    BASE_DIR: Path = Path(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DATA_DIR: Path = BASE_DIR / "data"   # Onde fica o SQLite
    LOG_DIR: Path = BASE_DIR / "logs"    # Onde ficam os logs
    PROJECT_ROOT: Path = BASE_DIR.parent.parent  # hmcpf-system/ (raiz do novo projeto)

    # ── Banco Legado (Recepção) ───────────────────────────────
    # Caminho para o hospital.db existente no sistema HMPCF legado
    # Deixe vazio para usar detecção automática
    LEGACY_DB_PATH: str = ""


# --- INSTÂNCIA ÚNICA (SINGLETON) ---
# Importamos 'settings' em qualquer módulo que precisar:
#   from app.core.config import settings
#   print(settings.DEBUG)
settings = Settings()
