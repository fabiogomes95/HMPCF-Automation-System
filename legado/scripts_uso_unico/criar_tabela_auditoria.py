"""
criar_tabela_auditoria.py
==========================
Cria a tabela `logs_auditoria` no PostgreSQL de produção, se ainda não
existir. Idempotente — não recria nem mexe em nada que já exista, e não
toca nas outras tabelas.

Mesmo padrão de scripts/criar_tabelas_auth.py (item #1 da lista de
prioridades) — o repo ainda não usa Alembic.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\criar_tabela_auditoria.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.models.log_auditoria import LogAuditoria  # noqa: E402


def main() -> None:
    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(bind=engine, tables=[LogAuditoria.__table__])
    print("OK: tabela 'logs_auditoria' garantida (criada agora ou já existente).")


if __name__ == "__main__":
    main()
