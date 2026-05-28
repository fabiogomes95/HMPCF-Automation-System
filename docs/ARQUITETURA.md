# Arquitetura HMPCF — Backend Modular

## Visão Geral

O HMPCF adota a mesma filosofia arquitetural do **BarrioERP**: camadas bem definidas,
separação de responsabilidades, PostgreSQL como única fonte de verdade, e migrations
versionadas via Alembic.

---

## Estrutura de Diretórios

```
hmpcf-system/
├── backend/                    # Aplicação FastAPI
│   ├── app/                    # Código-fonte do novo sistema
│   │   ├── main.py             # Entrypoint FastAPI (lifespan, CORS, exception handlers)
│   │   ├── core/
│   │   │   ├── config.py       # Settings via pydantic-settings (lê .env)
│   │   │   └── exceptions.py   # Exceções de domínio (agnósticas a HTTP)
│   │   ├── database/
│   │   │   ├── base.py         # DeclarativeBase SQLAlchemy
│   │   │   └── session.py      # Engine async, SessionLocal, get_db()
│   │   ├── models/             # SQLAlchemy ORM Models
│   │   ├── schemas/            # Pydantic v2 Schemas (Create/Update/Response)
│   │   ├── repositories/       # Queries isoladas (BaseRepository + específicos)
│   │   ├── services/           # Regras de negócio
│   │   └── api/
│   │       ├── deps.py         # Tipos anotados (DBSession)
│   │       └── v1/
│   │           ├── router.py   # Agrega todos os endpoints v1
│   │           └── endpoints/  # Um arquivo por recurso
│   ├── alembic/                # Migrations versionadas
│   │   └── versions/           # Histórico de migrations
│   ├── alembic.ini             # Configuração Alembic
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                    # Variáveis de ambiente (não versionado)
│
├── docker/                     # Infraestrutura Docker
│   └── docker-compose.yml      # PostgreSQL + pgAdmin + backend
├── docs/architecture/          # Esta documentação
├── migrations/                 # README sobre o processo de migrations
├── scripts/                    # Scripts utilitários (ETL, etc.)
├── legacy_reference/           # Documentação do sistema legado
└── frontend/                   # Frontend React/Vite (intocado)
```

---

## Fluxo de Dados

```
HTTP Request
    │
    ▼
FastAPI Endpoint  (app/api/v1/endpoints/*.py)
    │  Injeta DBSession via Depends(get_db)
    │  Valida request com Schema Pydantic
    ▼
Service           (app/services/*.py)
    │  Regras de negócio
    │  Lança exceções de domínio (NotFoundError, ConflictError...)
    ▼
Repository        (app/repositories/*.py)
    │  Queries SQLAlchemy async
    │  Nunca faz commit — delega para get_db()
    ▼
PostgreSQL        (via asyncpg + SQLAlchemy 2.x)
    │
    ▼
Schema Response   (Pydantic .model_validate(orm_object))
    │
    ▼
HTTP Response
```

---

## Padrão de Camadas

### 1. API (Endpoints)
- Responsabilidade: receber request, injetar dependências, retornar response
- **Nunca** contém lógica de negócio
- **Nunca** acessa banco diretamente
- Usa tipos anotados: `DBSession = Annotated[AsyncSession, Depends(get_db)]`

### 2. Service
- Responsabilidade: regras de negócio, orquestração
- Lança `HMPCFError` (não `HTTPException`)
- Recebe sessão assíncrona no `__init__`
- Instancia o Repository com a **mesma sessão** (mesma transação)

### 3. Repository
- Responsabilidade: queries SQLAlchemy isoladas
- Herda `BaseRepository[ModelT]` com CRUD genérico
- Métodos específicos para buscas de domínio (ex: `get_by_cpf`, `search`)
- **Nunca** faz `commit` — apenas `flush + refresh`

### 4. Model (SQLAlchemy)
- Define a estrutura da tabela e mapeamento ORM
- Usa `Mapped[]` e `mapped_column()` do SQLAlchemy 2.x
- Colunas com nomes legacy (ex: `"NUM_CPF"`) mapeadas para atributos snake_case

### 5. Schema (Pydantic v2)
- `{Entidade}Create` → campos para criação
- `{Entidade}Update` → todos opcionais, semântica PATCH
- `{Entidade}Response` → representação completa na resposta
- `from_attributes=True` para ler objetos SQLAlchemy diretamente

---

## Exception Handlers

As exceções de domínio em `app/core/exceptions.py` são capturadas em `main.py`
e convertidas para respostas HTTP padronizadas:

| Exceção de Domínio | HTTP Status | Quando usar |
|--------------------|-------------|-------------|
| `NotFoundError` | 404 | Recurso não encontrado |
| `ConflictError` | 409 | Duplicata (CPF, CNS) |
| `BusinessRuleError` | 422 | Regra de negócio violada |
| `ValidationError` | 422 | Dados inválidos |
| `HMPCFError` | 500 | Erro genérico de domínio |

Formato padrão de resposta de erro:
```json
{"error": "ConflictError", "message": "Paciente com CPF 12345678900 já existe"}
```

---

## PostgreSQL

### Conexão
- **FastAPI**: `postgresql+asyncpg://` (assíncrono, pool gerenciado pelo SQLAlchemy)
- **Alembic**: `postgresql+psycopg2://` (síncrono, apenas para migrations)

### Pool de conexões
```
DATABASE_POOL_SIZE=10     # conexões permanentes no pool
DATABASE_MAX_OVERFLOW=20  # conexões extras sob demanda
DATABASE_POOL_PRE_PING=true  # testa conexões antes de usar
```

### Tabela pacientes
Todas as colunas usam **snake_case** (renomeadas em 2026-05-24 via `recreate_pacientes.py`).
O SQLAlchemy mapeia diretamente sem aliases — atributo Python = nome da coluna no banco.

---

## Docker

### Desenvolvimento local
```bash
# Subir apenas PostgreSQL (já em execução via docker-compose.yml na raiz)
docker compose up -d

# Subir stack completa (PG + pgAdmin + backend)
cd docker
docker compose up -d
```

### Serviços
| Serviço | Porta | Credenciais |
|---------|-------|-------------|
| PostgreSQL | 5432 | postgres / hmpcf2024 |
| pgAdmin | 5050 | admin@hmpcf.local / admin |
| Backend | 8000 | — |

---

## Alembic — Migrations

```bash
cd backend

# Banco já existe (dados migrados via ETL)
alembic stamp 0001

# Criar nova migration
alembic revision --autogenerate -m "add_coluna_xyz"

# Aplicar
alembic upgrade head

# Ver histórico
alembic history --verbose
```

**Regra**: Toda alteração de schema via Alembic. Nunca manualmente.

---

## Legado (Removido)

Os arquivos legados foram removidos em 2026-05-25:

| Arquivo | Motivo |
|---------|--------|
| `backend/main.py` | Entrypoint legado concorrente |
| `backend/database.py` | Conexão SQLite (apenas routes legados usavam) |
| `backend/database_pg.py` | Conexão PostgreSQL raw (substituída por SQLAlchemy async) |
| `backend/routes/` | Rotas SQLite + PostgreSQL raw |

O único módulo ativo é `backend/app/` com FastAPI modular + SQLAlchemy async + PostgreSQL.

---

## Módulos

| Módulo | Status | Rota |
|--------|--------|------|
| Pacientes | Implementado | `/api/v1/pacientes` |
| Recepção | Implementado | `/api/v1/recepcao` |
| Terminal | Implementado | `/api/v1/terminal` |
| Busca Agrupada | Implementado | `GET /api/v1/recepcao/pacientes/agrupado?q=...` |
| Testes | 21 testes | `backend/tests/` |
| Classificação | Não iniciado | — |
| Relatórios | Não iniciado | — |

### Endpoints da Busca Agrupada

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/recepcao/pacientes/agrupado?q=...` | Pacientes únicos com total de entradas e última data |
| GET | `/api/v1/recepcao/paciente/{id}` | Histórico completo de atendimentos de um paciente |

> Ver detalhes completos das sessões em `docs/sessao_2026-05-24.md` e `docs/sessao_2026-05-25.md`.
