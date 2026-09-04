# HMPCF Automation System

🇺🇸 [Read in English](README.md)

> Sistema de automação hospitalar para recepção digital, painel gerencial em
> tempo real e faturamento BPA/SUS. Desenvolvido para o Hospital Municipal
> Pres. Café Filho — Extremoz/RN, Brasil.

Arquitetura moderna com **FastAPI + PostgreSQL + React/Vite** para a
recepção, um **painel gerencial em Streamlit** para coordenação/TI, e um
serviço **Flask + Firebird** dedicado à geração dos arquivos de
faturamento BPA/SUS.

---

## Visão Geral

O sistema é composto por três frentes independentes, todas lendo o mesmo
PostgreSQL como fonte única de verdade:

1. **Recepção digital** (`backend/` + `frontend/`) — cadastro e atendimento
   de pacientes, em produção no terminal da recepção do hospital.
2. **Painel gerencial** (`dashboard/`) — visão em tempo real para
   coordenadores e TI: histórico diário, busca de paciente e importação de
   planilhas manuais. Processo independente, somente leitura por padrão,
   não interfere na recepção.
3. **Faturamento BPA/SUS** (`bpa/`) — aplicação Flask separada que gera os
   arquivos posicionais BPA-I (um por profissional/categoria, por
   competência) a partir dos atendimentos do PostgreSQL, migrando os dados
   para a base Firebird (`BPAMAG.GDB`) exigida pelo BPA Magnético do
   Ministério da Saúde.

O **sistema legado** (`legado/`, Python/Eel/SQLite) foi **descontinuado em
02/07/2026** — permanece no repositório apenas como referência histórica e
não recebe mais manutenção nem deploy.

---

## Status

| Módulo | Situação |
|--------|----------|
| Recepção digital (FastAPI + React) | **Em produção** |
| Painel gerencial (Streamlit) | **Em produção** |
| Faturamento BPA/SUS (geração de arquivo posicional) | **Em produção** |
| Importação de planilhas manuais (deduplicação, correção de fuso/turno) | **Em produção** |
| Início automático (Tarefa Agendada + watchdog) | Configurado |
| Autenticação/autorização na API | **Não implementada** — sistema pensado pra rede local isolada do hospital; ver [Segurança](#segurança-e-limitações-conhecidas) |
| Testes automatizados (backend) | 21 testes |
| Testes automatizados (frontend / dashboard / bpa) | Ainda não há |
| Sistema legado (Firebird/Eel) | **Descontinuado** — mantido só como referência |

---

## Funcionalidades

- CRUD de pacientes com busca agrupada por nome, CPF ou CNS e histórico
  completo de atendimentos.
- Registro de atendimentos vinculado a cada paciente, com paginação e
  busca livre.
- Painel gerencial somente leitura: KPIs diários (volume, sexo, faixa
  etária, bairro), histórico completo de um dia específico e busca de
  paciente em toda a base.
- Importação de planilha manual (`.tsv`) que compara com o banco e
  importa só o que falta, com deduplicação e correção automática de data
  pra atendimentos de plantão noturno.
- Geração do BPA-I seguindo o layout posicional oficial do DATASUS (350
  caracteres), com folha/sequência contínua por competência.
- Migração PostgreSQL → Firebird pro cadastro do BPA Magnético
  (`CADCNS`), com validação de CPF antes de migrar.
- Boletim de atendimento A4 pra impressão na recepção.

---

## Stack

| Componente | Stack |
|---|---|
| Backend (API da recepção) | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · asyncpg · Pydantic v2 · pytest |
| Frontend (interface da recepção) | React 18.3 · Vite 5.4 · axios |
| Painel gerencial | Streamlit · pandas · Plotly · SQLAlchemy (síncrono, psycopg2) |
| Faturamento BPA | Flask · firebirdsql · psycopg2 · pandas/openpyxl |
| Banco de dados | PostgreSQL 16 — instalação nativa, **não containerizado** |
| Legado (descontinuado) | Python · Eel · SQLite |

---

## Pré-requisitos

- Windows 10/11 (ambiente de produção — rede LAN do hospital, uptime 24h)
- Python 3.12+
- Node.js 18+ e npm (só pra buildar o frontend)
- PostgreSQL 16, instalado nativamente (sem Docker — ver nota em [Banco de Dados](#banco-de-dados))
- Cliente Firebird + uma base `BPAMAG.GDB`, só pro módulo `bpa/`

TODO: fixar versão exata de Node.js/npm se o projeto adotar `.nvmrc` ou matriz de CI no futuro.

---

## Instalação

Cada aplicação tem seu próprio ambiente virtual/dependências, exceto o
`bpa/`, que reaproveita o do `dashboard/` (ver [Como Rodar](#como-rodar)
abaixo).

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp .env.example .env   # preencha POSTGRES_PASSWORD
```

### Frontend

```bash
cd frontend
npm install
npm run build   # gera frontend/dist, servido pelo backend em produção
```

### Dashboard (também usado pra rodar o `bpa/`)

```bash
cd dashboard
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp .env.example .env   # preencha as credenciais FIREBIRD_*
```

### Faturamento BPA

```bash
cd bpa
cp .env.example .env   # ajuste BPA_LOTES_DIR / BPA_SAIDA_DIR pra esta máquina
```

Sem ambiente virtual próprio — `bpa/app.py` roda em cima do
`dashboard/.venv` (ver `bpa/iniciar.bat`). O `bpa/requirements.txt` existe
só pra documentar o que esse ambiente compartilhado precisa, caso o
`bpa/` ganhe um venv próprio no futuro.

---

## Configuração

Credenciais reais nunca são commitadas — `.env` está coberto em todo
lugar pelo `.gitignore` (`.env`, `**/.env`). Copie o `.env.example`
correspondente em cada pasta e preencha com valores reais.

O `bpa/app.py` carrega os três `.env`, nesta ordem (o primeiro valor
encontrado vale): `bpa/.env` → `dashboard/.env` → `backend/.env`. Já o
`dashboard/db.py` lê `backend/.env` direto pra sua conexão (somente
leitura) com o PostgreSQL.

### `backend/.env` — PostgreSQL, API

| Variável | Padrão | Descrição |
|---|---|---|
| `APP_NAME` | `HMPCF` | Nome exibido nos metadados OpenAPI do FastAPI |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` — esconde `/docs`, `/redoc`, `/openapi.json` em produção |
| `POSTGRES_HOST` | `localhost` | Host do PostgreSQL |
| `POSTGRES_PORT` | `5432` | Porta do PostgreSQL |
| `POSTGRES_USER` | `postgres` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | — (obrigatório) | Senha do PostgreSQL — passa por URL-encode automático antes de montar a connection string |
| `POSTGRES_DB` | `hmpcf` | Nome do banco |
| `DATABASE_POOL_SIZE` | `10` | Tamanho do pool async do SQLAlchemy |
| `DATABASE_MAX_OVERFLOW` | `20` | Conexões extras sob demanda |
| `DATABASE_POOL_PRE_PING` | `true` | Testa conexões antes de reusar |
| `CORS_ORIGINS` | `["*"]` | Seguro como `["*"]` em produção porque frontend e backend dividem a mesma origem na rede local |
| `TEST_POSTGRES_DB` | `hmpcf_test` | Banco usado pela suíte pytest — nunca apontar pro `hmpcf` |

### `dashboard/.env` — Firebird (usado pela migração do BPA)

| Variável | Padrão | Descrição |
|---|---|---|
| `FIREBIRD_PATH` | `C:\BPA\BPAMAG.GDB` | Caminho da base Firebird local |
| `FIREBIRD_USER` | `SYSDBA` | Usuário do Firebird |
| `FIREBIRD_PASSWORD` | — (obrigatório) | Senha do Firebird |
| `BPA_LOTES_DIR` | `dashboard/bpa_lotes` (relativo ao repo) | Pasta com os lotes brutos `.txt` de digitação diária |
| `BPA_SAIDA_DIR` | *(vazio → `~/Downloads`)* | Pasta de saída do arquivo BPA-I gerado |

### `bpa/.env` — ajustes por máquina do app Flask

| Variável | Padrão | Descrição |
|---|---|---|
| `BPA_LOTES_DIR` | `bpa/bpa_lotes` (relativo ao repo, se não definida) | Mesma variável acima, sobrescrevível por máquina |
| `BPA_SAIDA_DIR` | *(vazio → `~/Downloads`)* | Mesma variável acima |
| `POSTGRES_HOST` | herdado de `backend/.env` | Sobrescreve quando o Flask roda numa máquina com PostgreSQL em host diferente |
| `BPA_DIGITACAO_PORT` | `8503` | Porta do app Flask |

---

## Como Rodar

### Recepção (Windows, produção)

```bat
INICIAR.bat
```

Sobe o backend (`uvicorn`, porta 8001 — que também serve o frontend
buildado em `frontend/dist/`) e abre o navegador. Registrado como Tarefa
Agendada do Windows (`HMPCF-Backend`) — inicia no boot e reinicia
automaticamente se cair (watchdog em
`scripts/windows/watchdog_backend.vbs`).

> Existem mais dois launchers pro mesmo backend
> (`scripts/windows/ABRIR_HMPCF.bat`, `scripts/windows/iniciar_sistema.vbs`)
> — TODO: consolidar em um só depois de confirmar, numa máquina de teste,
> qual deles está de fato registrado no Agendador de Tarefas da máquina de
> produção.

### Recepção (desenvolvimento)

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8001
```

```bash
cd frontend
npm run dev
```

O servidor de dev do Vite redireciona `/api` pra
`http://desktop-9c4s1co:8001` (ver `frontend/vite.config.js`) — esse
hostname é o da máquina de produção; ajuste o proxy se estiver rodando o
backend em outro lugar.

### Painel Gerencial (Streamlit)

```bash
cd dashboard
.venv\Scripts\streamlit run app.py
```

Sobe em `http://localhost:8502` (rede local:
`http://<ip-da-máquina>:8502`). Launcher em
`scripts/windows/ABRIR_DASHBOARD.bat`, também registrado como Tarefa
Agendada própria, independente do backend.

### Faturamento BPA/SUS (Flask)

```bash
cd bpa
..\dashboard\.venv\Scripts\python.exe app.py
```

Sobe em `http://localhost:8503`. Exige acesso de leitura ao PostgreSQL
(atendimentos) e à base Firebird local do BPA Magnético. Launchers de
atalho de área de trabalho: `bpa/iniciar.bat`, `bpa/start_bpa.vbs`
(silencioso, sem janela de console — ver `bpa/README.md`).

---

## Estrutura de Pastas

```
📦 HMPCF-Automation-System
 ┣ 📂 backend/                       # API FastAPI — recepção digital
 ┃  ┗ 📂 app/
 ┃     ┣ 📜 main.py                  # Entrypoint (lifespan, CORS, exception handlers)
 ┃     ┣ 📂 core/                    # Config (pydantic-settings) + exceções de domínio
 ┃     ┣ 📂 database/                # Engine async, SessionLocal
 ┃     ┣ 📂 models/                  # SQLAlchemy ORM (pacientes, atendimentos)
 ┃     ┣ 📂 schemas/                 # Pydantic v2
 ┃     ┣ 📂 repositories/            # Queries isoladas
 ┃     ┣ 📂 services/                # Regras de negócio
 ┃     ┗ 📂 api/v1/endpoints/        # pacientes · recepcao · terminal
 ┃  ┗ 📂 tests/                      # 21 testes (pytest)
 ┣ 📂 frontend/                      # React + Vite — terminal de digitação da recepção
 ┣ 📂 dashboard/                     # Streamlit — painel gerencial (TI/coordenação)
 ┃  ┣ 📜 app.py                      # KPIs, gráficos (volume, sexo, idade, bairro)
 ┃  ┣ 📜 db.py                       # Conexão somente leitura + utilitários compartilhados
 ┃  ┗ 📂 pages/                      # Histórico diário · importação mensal · busca de paciente
 ┣ 📂 bpa/                           # Flask — geração BPA-I e migração PG→Firebird
 ┃  ┣ 📜 app.py                      # Digitação, geração do BPA-I, migração
 ┃  ┣ 📜 bpa_gerador.py              # Lógica central do BPA-I (layout, checksum, folha/seq)
 ┃  ┣ 📂 auditoria_mensal/           # Scripts de resposta a incidente, uso ativo
 ┃  ┗ 📂 legado/                     # Backups/arquivos pontuais arquivados dentro do bpa/
 ┣ 📂 docs/                          # Documentação viva (arquitetura, deploy, instalação)
 ┃  ┗ 📂 historico/                  # Registros de um momento específico (auditorias, migrações)
 ┣ 📂 scripts/
 ┃  ┣ 📂 bpa/                        # Ferramentas de linha de comando pro app Flask
 ┃  ┣ 📂 importacao/                 # Pipeline mensal de importação (+ legado/ pra one-offs)
 ┃  ┣ 📂 migrations/legado/          # Migração SQLite→PostgreSQL, já executada
 ┃  ┗ 📂 windows/                    # Launchers, backup, registro na Tarefa Agendada
 ┣ 📂 legado/                        # Sistema original — descontinuado, mantido como referência
 ┃  ┗ 📂 docker-compose/             # Setup Docker descontinuado (ver NOTA.md)
 ┗ 📜 INICIAR.bat                    # Launcher da recepção (backend + frontend), produção
```

---

## API (Backend)

Prefixo base: `/api/v1`. Documentação interativa (só fora de produção):
`http://localhost:8001/docs`.

### `pacientes`

| Método | Rota | Descrição |
|---|---|---|
| GET | `/pacientes` | Listar pacientes (paginado, busca opcional `q` — nome/CPF/CNS) |
| GET | `/pacientes/busca` | Buscar um paciente por CPF ou CNS (`documento`) |
| GET | `/pacientes/{id}` | Buscar paciente por ID |
| POST | `/pacientes` | Criar paciente |
| PUT | `/pacientes/{id}` | Atualizar paciente |
| DELETE | `/pacientes/{id}` | Remover paciente |

### `recepcao`

| Método | Rota | Descrição |
|---|---|---|
| GET | `/recepcao` | Listar atendimentos, mais recentes primeiro (paginado, `q` opcional) |
| GET | `/recepcao/pacientes/agrupado` | Busca agrupada — pacientes únicos com total de entradas (`q` obrigatório, mín. 3 caracteres) |
| GET | `/recepcao/recentes` | Últimos atendimentos registrados |
| GET | `/recepcao/paciente/{paciente_id}` | Histórico completo de atendimentos de um paciente |
| GET | `/recepcao/{id}` | Detalhe completo de um atendimento |
| POST | `/recepcao` | Registrar novo atendimento |
| PUT | `/recepcao/{id}` | Atualizar atendimento |
| DELETE | `/recepcao/{id}` | Remover atendimento |

### `terminal`

| Método | Rota | Descrição |
|---|---|---|
| POST | `/terminal/start` | Iniciar sessão de terminal |
| POST | `/terminal/ping` | Ping de keep-alive do terminal |

### Infra

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Health check — sem autenticação, sem dados sensíveis |

---

## Banco de Dados

PostgreSQL como única fonte de verdade. **TODO**: a documentação antiga
citava migrations gerenciadas via Alembic, mas não existe `alembic.ini`,
pasta `alembic/` nem dependência `alembic` neste repositório atualmente —
falta confirmar e documentar como o schema é de fato criado/versionado
hoje (ou reintroduzir o Alembic, se essa ainda for a intenção).

---

## Testes

```bash
cd backend
pytest tests/ -v
```

21 testes cobrindo `pacientes`, `recepcao` e `terminal` (só o backend —
frontend, dashboard e `bpa/` ainda não têm suíte automatizada). O
frontend tem o Playwright instalado como dependência de desenvolvimento,
mas ainda não existe nenhum arquivo de teste — TODO se cobertura
end-to-end entrar no roadmap.

---

## Deploy

Produção roda nativamente no Windows (sem Docker, sem containers) no PC
da recepção do hospital, pela rede LAN interna. Guias completos
passo a passo:

- `docs/DEPLOY_HOSPITAL.md` — guia geral de implantação
- `docs/INSTALACAO_PC_RECEPCAO.md` — preparar um PC de recepção do zero
- `docs/INSTALACAO_BPA_MIGRACAO.md` — instalar o app BPA + migração PG→Firebird numa máquina nova

---

## Segurança e Limitações Conhecidas

Este sistema foi desenhado pra operar dentro da **rede local isolada do
hospital**, não exposto à internet. Pontos relevantes pra quem for
implantar ou operar:

- **Sem autenticação/autorização na API** ainda — qualquer dispositivo
  com acesso à rede local do backend pode ler/escrever atendimentos.
  Compensar com segmentação de rede adequada (perfil de firewall
  `Domain`/`Private`, nunca `Public`, e VLAN dedicada se possível) até a
  autenticação ser implementada.
- **Segredos vivem só em arquivos `.env`** (nunca em scripts ou docs
  versionados) — ao gerar uma senha nova, evite caracteres delimitadores
  de URL (`@ : / ? #`) em strings de conexão, ou garanta que o código
  faça URL-encode antes (o backend já faz isso pro PostgreSQL).
- **Dados sensíveis** (CPF, CNS, endereço, dados de saúde) — evite logar
  esses valores em texto puro em scripts de importação/migração; prefira
  logar só identificadores internos em caso de erro.
- **Backups** (`scripts/windows/backup_postgres.bat`) geram dump em texto
  puro localmente — combine com controle de acesso ao diretório de
  backup e rotação (já implementado, 30 dias).

Contribuições que fecham essas lacunas (auth de sessão, RBAC básico,
criptografia de backup) são bem-vindas.

---

## Sistema Legado

O sistema original (`legado/`, Python/Eel/SQLite) foi **oficialmente
descontinuado em 02/07/2026**. Permanece no repositório apenas como
referência histórica e fallback documental — não recebe deploy nem
manutenção. Consulte `legado/passo_a_passo.md` se precisar entender como
ele operava.

---

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação em
produção sem autorização explícita do autor.
