# Legacy Reference — HMPCF

Este diretório documenta a arquitetura do sistema **legado** (pré-migração).

## O que é o legado

O sistema legado usa:
- **SQLite** (`hospital.db`) como banco de dados
- **psycopg2** com queries SQL diretas (sem ORM)
- Roteadores FastAPI sem separação de camadas

## Arquivos legados (em `backend/`, não modificar)

| Arquivo | Descrição |
|---------|-----------|
| `backend/main.py` | App original com routers v1 (SQLite) e v2 (PG direto) |
| `backend/database.py` | Conexão SQLite com `sqlite3` nativo |
| `backend/database_pg.py` | Conexão PostgreSQL com psycopg2 (pool simples) |
| `backend/routes/pacientes.py` | Endpoints SQLite — mapeamento Frontend↔DB manual |
| `backend/routes/pacientes_pg.py` | Endpoints PG v2 — queries diretas psycopg2 |
| `backend/routes/atendimentos.py` | Endpoints de atendimento (SQLite) |
| `backend/routes/terminal.py` | Endpoints de terminal (SQLite) |

## Regras

1. **NÃO modificar** nenhum arquivo listado acima
2. **NÃO alterar** `hospital.db`
3. **NÃO misturar** código legado com o novo sistema em `backend/app/`

## Novo sistema

O novo backend está em `backend/app/` — arquitetura modular com:
- SQLAlchemy 2.x async
- Pydantic v2
- Alembic para migrations
- Camadas: API → Service → Repository → Model

Veja `docs/architecture/README.md` para a documentação completa.
