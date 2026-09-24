"""
criar_tabela_bpa_lotes.py
=========================
Cria a tabela `bpa_lotes_backup` (cópia dos lotes de digitação do BPA de cada
notebook) e libera o usuário `bpa_leitura` pra gravar SÓ nela. Idempotente:
não recria nem mexe em nada que já exista, e não toca nas outras tabelas.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\criar_tabela_bpa_lotes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.models.bpa_lote_backup import BpaLoteBackup  # noqa: E402

GRANTS = [
    # SELECT: o INSERT ... ON CONFLICT DO UPDATE do BPA local precisa ler a tabela
    "GRANT SELECT, INSERT, UPDATE ON bpa_lotes_backup TO bpa_leitura",
    "GRANT USAGE ON SEQUENCE bpa_lotes_backup_id_seq TO bpa_leitura",
]


def main() -> None:
    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(bind=engine, tables=[BpaLoteBackup.__table__])
    print("OK: tabela 'bpa_lotes_backup' garantida (criada agora ou já existente).")
    with engine.begin() as con:
        existe = con.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'bpa_leitura'")).scalar()
        if not existe:
            print("AVISO: usuário bpa_leitura não existe -- permissões não aplicadas.")
            return
        for g in GRANTS:
            con.execute(text(g))
    print("OK: bpa_leitura pode gravar em bpa_lotes_backup (e só nela).")


if __name__ == "__main__":
    main()
