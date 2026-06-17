# HMPCF Automation System

> Sistema de automação hospitalar para recepção digital, painel gerencial em
> tempo real, faturamento BPA/SUS e auditoria. Desenvolvido para o Hospital
> Municipal Pres. Café Filho — Extremoz/RN, Brasil.

Migração do sistema legado (Python/Eel/SQLite) para uma arquitetura moderna
com **FastAPI + PostgreSQL + React/Vite**, com um **painel gerencial em
Streamlit** rodando em paralelo para coordenação e TI.

---

## Visão Geral

O HMPCF Automation System é composto por três frentes independentes, todas
lendo o mesmo PostgreSQL:

1. **Recepção digital** (`backend/` + `frontend/`) — cadastro e atendimento de
   pacientes, em produção no terminal da recepção do hospital.
2. **Painel gerencial** (`dashboard/`) — visão em tempo real para
   coordenadores e TI, com histórico diário, busca de paciente e importação
   de planilhas manuais. Processo independente, somente leitura por padrão,
   não interfere na recepção.
3. **Sistema legado** (`legado/`) — Python/Eel/SQLite, mantido íntegro como
   referência e fallback.

---

## Status

| Módulo | Situação |
|--------|----------|
| Recepção digital (FastAPI + React) | **Em produção** |
| Painel gerencial (Streamlit) | **Em produção** |
| Importação de planilhas manuais (deduplicação, correção de fuso/turno) | **Em produção** |
| Início automático (Tarefas Agendadas + watchdog) | **Configurado** |
| Autenticação / sessão multi-usuário | A fazer |
| Faturamento BPA/SUS (geração TXT posicional) | A fazer |
| Painel de gestão legado (Firebird) | Em descontinuação |
| Testes automatizados (backend) | 21 testes |

---

## Arquitetura

```
📦 HMPCF-Automation-System
 ┣ 📂 backend/                       # API FastAPI — recepção digital
 ┃  ┗ 📂 app/
 ┃     ┣ 📜 main.py                  # Entrypoint (lifespan, CORS, handlers)
 ┃     ┣ 📂 core/                    # Config (pydantic-settings) + exceções
 ┃     ┣ 📂 database/                # Engine async, SessionLocal
 ┃     ┣ 📂 models/                  # SQLAlchemy ORM (pacientes, atendimentos)
 ┃     ┣ 📂 schemas/                 # Pydantic v2
 ┃     ┣ 📂 repositories/            # Queries isoladas
 ┃     ┣ 📂 services/                # Regras de negócio
 ┃     ┗ 📂 api/v1/endpoints/        # Pacientes · Recepção · Terminal
 ┣ 📂 frontend/                      # React + Vite — terminal de digitação
 ┣ 📂 dashboard/                     # Streamlit — painel gerencial (TI/coordenação)
 ┃  ┣ 📜 app.py                      # KPIs, gráficos (volume, sexo, idade, bairros)
 ┃  ┣ 📜 db.py                       # Conexão somente leitura + utilitários compartilhados
 ┃  ┣ 📜 importador.py               # Parser e importação de planilhas manuais
 ┃  ┗ 📂 pages/
 ┃     ┣ 📜 1_Historico_Diario.py    # Histórico do dia, filtrável (hoje/ontem/data)
 ┃     ┣ 📜 2_Importar_Planilha_Mensal.py  # Upload .tsv → compara e importa faltantes
 ┃     ┗ 📜 3_Buscar_Paciente.py     # Busca por nome/CPF/CNS → histórico completo
 ┣ 📂 docker/                        # Stack completa: PG + pgAdmin + backend
 ┣ 📂 docs/                          # Arquitetura, histórico e decisões técnicas
 ┣ 📂 scripts/                       # Scripts utilitários (backup, BPA, importação)
 ┣ 📂 legado/                        # Sistema original completo (referência)
 ┣ 📜 docker-compose.yml             # PostgreSQL local (desenvolvimento)
 ┣ 📜 INICIAR.bat                    # Launcher da recepção (backend + frontend)
 ┗ 📜 ABRIR_DASHBOARD.bat            # Launcher do painel gerencial
```

---

## Como Rodar

### Recepção (Windows, produção)

```bat
INICIAR.bat
```

Sobe o backend (`uvicorn`, porta 8001) e abre o navegador. Já está registrado
como Tarefa Agendada (`HMPCF-Backend`) — inicia no boot e reinicia
automaticamente se cair.

### Painel Gerencial (Streamlit)

```bat
ABRIR_DASHBOARD.bat
```

Sobe em `http://localhost:8502` (rede local: `http://<ip-da-maquina>:8502`).
Também registrado como Tarefa Agendada (`HMPCF-Dashboard`), independente do
backend — pode ser acessado de qualquer máquina na rede sem instalar nada
localmente.

```bash
cd dashboard
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

### Docker (banco de dados local, desenvolvimento)

```bash
# Apenas PostgreSQL
docker compose up -d

# Stack completa: PG + pgAdmin + backend
cd docker
docker compose up -d
```

| Serviço | Porta | Acesso |
|---------|-------|--------|
| Backend API (recepção) | 8001 | http://localhost:8001/docs |
| Painel Gerencial | 8502 | http://localhost:8502 |
| Frontend (dev) | 5173 | http://localhost:5173 |
| PostgreSQL | 5432 | — |
| pgAdmin | 5050 | admin@hmpcf.local / admin |

### Configuração

```bash
cp backend/.env.example backend/.env
# edite com suas credenciais — o dashboard reaproveita esse mesmo .env
```

---

## Painel Gerencial (Dashboard)

Aplicação **Streamlit independente**, com seu próprio ambiente virtual e
porta — não compartilha processo, código ou dependências com o backend da
recepção. Lê o PostgreSQL em modo somente leitura por padrão; escreve apenas
nas telas explicitamente destinadas a isso (importação de planilha), sempre
com confirmação manual antes de gravar.

**Painel principal** — KPIs (hoje / semana / mês / total), volume diário,
distribuição por sexo, faixa etária e bairro de origem.

**Histórico Diário** — lista completa de atendimentos de um dia específico,
com nome, CPF, CNS, nascimento, idade, sexo, endereço e telefone.

**Buscar Paciente** — pesquisa por nome, CPF ou CNS, retornando todas as
entradas (data e horário) daquele paciente no sistema.

**Importar Planilha Mensal** — compara a planilha manual de plantão (`.tsv`)
com o banco e importa só os atendimentos que faltam (quando o plantão
registra no papel mas não digita no sistema). Trata os casos reais já
encontrados em produção:
- Deduplicação por paciente: mesmo registro de plantão ou horário a poucos
  minutos de distância → mantém só o lançamento mais recente.
- Correção automática de erro de digitação no ano do cabeçalho do plantão.
- Atendimentos de madrugada sob plantão noturno contam para o dia seguinte
  (mesma regra usada pela digitação real da recepção).
- Linhas com formato inesperado (ex: documento digitado no campo errado) são
  isoladas para revisão manual, nunca importadas silenciosamente.

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

---

## Endpoints Ativos (Backend)

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

Documentação interativa: http://localhost:8001/docs

---

## Testes

```bash
cd backend
pytest tests/ -v
```

21 testes cobrindo pacientes, recepção e terminal.

---

## Legado

O sistema original está íntegro em `legado/`, mantido como referência e
fallback. Consulte `legado/passo_a_passo.md` para instruções de operação.

---

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação
em produção sem autorização explícita do autor.
