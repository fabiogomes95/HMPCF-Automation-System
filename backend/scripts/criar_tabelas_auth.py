"""
criar_tabelas_auth.py
======================
Cria as tabelas `usuarios` e `sessoes` no PostgreSQL de produção, se ainda
não existirem. Idempotente — não recria nem mexe em nada que já exista,
e não toca nas tabelas `pacientes`/`recepcao_atendimentos`.

Não usa Alembic (o repo ainda não tem — ver docs/historico do projeto):
mesmo padrão de script standalone já usado pro schema atual.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\criar_tabelas_auth.py
"""

import sys
from pathlib import Path

# backend/ precisa estar no sys.path pra "import app..." funcionar
# quando o script é chamado como `python scripts/criar_tabelas_auth.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.models.sessao import Sessao  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402


def main() -> None:
    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(bind=engine, tables=[Usuario.__table__, Sessao.__table__])
    print("OK: tabelas 'usuarios' e 'sessoes' garantidas (criadas agora ou já existentes).")


if __name__ == "__main__":
    main()
