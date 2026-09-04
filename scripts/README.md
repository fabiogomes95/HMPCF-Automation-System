# Scripts — HMPCF

## migrations/legado/migrate_to_postgres.py

Script ETL de migração única: SQLite (`hospital.db`) → PostgreSQL.

Arquivado em `scripts/migrations/legado/` — já foi executado e não roda
mais em produção, mantido só como referência histórica.

Uso:
```bash
cd scripts/migrations/legado
python migrate_to_postgres.py --dry-run   # simula sem gravar
python migrate_to_postgres.py             # migração real
python migrate_to_postgres.py --truncate  # limpa e re-migra
```

**Status**: Executado — 28.672 registros migrados com sucesso (2026-05-23).
