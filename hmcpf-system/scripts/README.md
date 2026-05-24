# Scripts — HMPCF

## migrate_to_postgres.py

Script ETL de migração única: SQLite (`hospital.db`) → PostgreSQL.

Localização original: `hmcpf-system/migrate_to_postgres.py`

Uso:
```bash
cd hmcpf-system
python migrate_to_postgres.py --dry-run   # simula sem gravar
python migrate_to_postgres.py             # migração real
python migrate_to_postgres.py --truncate  # limpa e re-migra
```

**Status**: Executado — 28.672 registros migrados com sucesso (2026-05-23).
