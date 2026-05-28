# HMPCF Automation System

> Sistema de automação hospitalar para recepção digital, faturamento BPA/SUS,
> gestão administrativa e auditoria. Desenvolvido para o Hospital Municipal
> Pres. Café Filho — Extremoz/RN, Brasil.

Em migração ativa do sistema legado (Python/Eel/SQLite) para uma arquitetura
moderna com **FastAPI + PostgreSQL + React/Vite**, mantendo todas as
funcionalidades existentes e abrindo espaço para evolução.

---

## Visão Geral

O HMPCF Automation System integra recepção digital, automação BPA/SUS,
painel de gestão, auditoria e sincronização com Google Sheets, reduzindo
retrabalho manual e eliminando fichas em papel no hospital.

O sistema legado original (Python/Eel) continua em produção na pasta `legado/`
enquanto o novo sistema é construído em paralelo.

---

## Status da Migração

| Módulo | Legado | Novo Sistema |
|--------|--------|--------------|
| Recepção digital (cadastro, busca CPF/CNS/nome) | Produção | Em construção |
| API REST (FastAPI + PostgreSQL) | — | **Funcionando** |
| Busca agrupada de pacientes | — | **Funcionando** |
| Autenticação / sessão multi-usuário | Não tinha | A fazer |
| Faturamento BPA/SUS (geração TXT posicional) | Produção | A fazer |
| Automação RPA (digitação automática) | Produção | A fazer |
| Painel de gestão + Firebird | Produção | A fazer |
| Relatórios Excel/PDF | Produção | A fazer |
| Sincronização Google Sheets | Produção | A fazer |
| Testes automatizados | Zero | 21 testes (e crescendo) |

---

## Arquitetura do Novo Sistema

```
📦 HMPCF-Automation-System
 ┣ 📂 backend/                   # API FastAPI — único módulo ativo
 ┃  ┗ 📂 app/
 ┃     ┣ 📜 main.py              # Entrypoint FastAPI (lifespan, CORS, handlers)
 ┃     ┣ 📂 core/                # Config (pydantic-settings) + Exceções de domínio
 ┃     ┣ 📂 database/            # Engine async, SessionLocal, get_db()
 ┃     ┣ 📂 models/              # SQLAlchemy ORM (pacientes, atendimentos)
 ┃     ┣ 📂 schemas/             # Pydantic v2 (Create / Update / Response)
 ┃     ┣ 📂 repositories/        # Queries isoladas (BaseRepository + específicos)
 ┃     ┣ 📂 services/            # Regras de negócio
 ┃     ┗ 📂 api/v1/endpoints/    # Pacientes · Recepção · Terminal
 ┣ 📂 frontend/                  # React + Vite (intocado, aguarda integração)
 ┣ 📂 docker/                    # Stack completa: PG + pgAdmin + backend
 ┣ 📂 docs/                      # Arquitetura, histórico e decisões técnicas
 ┣ 📂 scripts/                   # Scripts ETL de uso único
 ┣ 📂 legado/                    # Sistema original completo (em produção)
 ┣ 📜 docker-compose.yml         # PostgreSQL local (desenvolvimento)
 ┗ 📜 INICIAR.bat                # Launcher Windows (backend + frontend)
```

---

## Como Rodar

### Windows (desenvolvimento)

```bat
INICIAR.bat
```

Sobe o backend (`uvicorn`, porta 8000) e o frontend Vite (porta 5173) e abre o navegador.

### Docker (banco de dados local)

```bash
# Apenas PostgreSQL
docker compose up -d

# Stack completa: PG + pgAdmin + backend
cd docker
docker compose up -d
```

| Serviço | Porta | Acesso |
|---------|-------|--------|
| Backend API | 8000 | http://localhost:8000/docs |
| Frontend | 5173 | http://localhost:5173 |
| PostgreSQL | 5432 | — |
| pgAdmin | 5050 | admin@hmpcf.local / admin |

### Configuração

```bash
cp backend/.env.example backend/.env
# edite com suas credenciais
```

---

## Banco de Dados

PostgreSQL como única fonte de verdade. Migrations versionadas via Alembic.

```bash
cd backend

# Aplicar migrations
alembic upgrade head

# Nova migration após alterar models
alembic revision --autogenerate -m "descricao"
```

**Dados migrados do legado:** 29.218 pacientes · 8.024 atendimentos

---

## Endpoints Ativos

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/pacientes` | Listar pacientes |
| POST | `/api/v1/pacientes` | Criar paciente |
| GET | `/api/v1/pacientes/{id}` | Buscar por ID |
| GET | `/api/v1/recepcao` | Listar atendimentos |
| POST | `/api/v1/recepcao` | Registrar atendimento |
| GET | `/api/v1/recepcao/pacientes/agrupado?q=...` | Busca agrupada com histórico |
| GET | `/api/v1/recepcao/paciente/{id}` | Histórico completo do paciente |
| GET | `/api/v1/terminal` | Status do sistema |

Documentação interativa: http://localhost:8000/docs

---

## Testes

```bash
cd backend
pytest tests/ -v
```

21 testes cobrindo pacientes, recepção e terminal.

---

## Legado

O sistema original está íntegro em `legado/` e continua em produção.
Consulte `legado/passo_a_passo.md` para instruções de operação do sistema legado.

---

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação
em produção sem autorização explícita do autor.
