from __future__ import annotations

import os
import sqlite3
from logging import getLogger
from pathlib import Path

from app.core.config import settings

logger = getLogger(__name__)


def _db_path() -> str:
    if settings.LEGACY_DB_PATH:
        return settings.LEGACY_DB_PATH

    base = settings.PROJECT_ROOT.parent
    candidates = [
        base / "hospital.db",
        settings.PROJECT_ROOT.parent / "hospital.db",
    ]
    for path in candidates:
        if path.exists():
            return str(path)

    fallback = settings.BASE_DIR.parent / "hospital.db"
    logger.warning("hospital.db nao encontrado nos caminhos padrao, tentando: %s", fallback)
    return str(fallback)


def get_legacy_conn() -> sqlite3.Connection:
    db_path = _db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"hospital.db nao encontrado: {db_path}")
    conn = sqlite3.connect(db_path, timeout=settings.SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    return conn
