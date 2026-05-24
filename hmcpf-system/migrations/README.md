# Migrations — HMPCF

## Tipos de Migration

### 1. Schema Migrations (Alembic)
Gerencia alterações na estrutura do banco de dados (CREATE TABLE, ALTER COLUMN, etc.)

```bash
# Executar do diretório backend/
cd backend

# Verificar histórico
alembic history

# Criar nova migration (detecta diferenças do model)
alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar migrations pendentes
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# BANCO JÁ EXISTENTE — marcar migration inicial como aplicada
alembic stamp 0001
```

### 2. Data Migrations (ETL)
Script de migração de dados do SQLite legado para o PostgreSQL.

```bash
# Localizado em: scripts/migrate_to_postgres.py (link)
# Original em:   hmcpf-system/migrate_to_postgres.py

# Dry-run (simula sem gravar)
python migrate_to_postgres.py --dry-run

# Migração real
python migrate_to_postgres.py

# Limpar tabela antes de re-migrar
python migrate_to_postgres.py --truncate
```

## Estado atual

| Migration | Status | Descrição |
|-----------|--------|-----------|
| 0001 | Aplicada via stamp | Tabela `pacientes` (migrada via ETL) |

## Convenções

- Toda alteração de schema DEVE passar pelo Alembic
- NUNCA alterar tabelas manualmente via psql/pgAdmin
- Migrations são versionadas junto com o código
