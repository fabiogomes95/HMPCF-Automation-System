"""
adicionar_coluna_sem_documento.py
==================================
Adiciona a coluna `sem_documento` (BOOLEAN, default false) na tabela
`pacientes`, se ainda não existir. Idempotente -- não mexe em nenhum dado
já existente (todo paciente atual passa a ter sem_documento=false).

Marca pacientes cadastrados sem CPF nem CNS (BPA/SUS agora tem uma opção
própria pra esse caso). Sem Alembic (o repo ainda não usa -- ver
docs/historico do projeto), mesmo padrão de scripts/criar_tabelas_auth.py.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\adicionar_coluna_sem_documento.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402


def main() -> None:
    engine = create_engine(settings.database_url_sync)
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE pacientes "
            "ADD COLUMN IF NOT EXISTS sem_documento BOOLEAN NOT NULL DEFAULT false"
        ))
    print("OK: coluna 'sem_documento' garantida em 'pacientes' (criada agora ou já existente).")


if __name__ == "__main__":
    main()
