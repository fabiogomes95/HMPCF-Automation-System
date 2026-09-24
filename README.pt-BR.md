# HMPCF Automation System

🇺🇸 [English summary](README.md) · este arquivo é a documentação completa

> Sistema de automação hospitalar para recepção digital, painel gerencial e
> faturamento BPA/SUS. Desenvolvido para o Hospital Municipal Pres. Café
> Filho — Extremoz/RN, Brasil.

Um sistema só, com uma interface web e menu por perfil (recepção,
faturamento, TI): **FastAPI + PostgreSQL + React/Vite** no servidor, e o
**BPA** rodando local em cada notebook do faturamento, junto do Firebird e
do BPA Magnético (offline).

---

## Visão Geral

O sistema é composto por três frentes independentes, todas lendo o mesmo
PostgreSQL como fonte única de verdade:

1. **Recepção digital** (`backend/` + `frontend/`) — cadastro e atendimento
   de pacientes, em produção no terminal da recepção do hospital.
2. **Painel gerencial** (aba **Painel** do próprio sistema, só TI) —
   visão em tempo real: atendimentos do dia e do plantão, comparação com o
   mês anterior, movimento por hora, perfil (sexo, faixa etária, bairro,
   cidade, procedência) e qualidade do cadastro. Rota `GET /api/v1/ti/painel`,
   só números agregados. Substituiu o antigo dashboard Streamlit, arquivado
   em `legado/dashboard_streamlit/`.
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
| Painel gerencial (aba Painel, TI) | **Em produção** |
| Faturamento BPA/SUS (geração de arquivo posicional) | **Em produção** |
| Importação de planilhas manuais (deduplicação, correção de fuso/turno) | **Em produção** |
| Início automático (serviço do Windows via nssm) | Configurado |
| Login, perfis (recepção, faturamento, TI) e auditoria | **Em produção** |
| Testes automatizados (backend / bpa) | pytest — rodam no CI a cada push |
| Testes automatizados (frontend) | Ainda não há |
| Sistema legado (Firebird/Eel) | **Descontinuado** — mantido só como referência |

---

## Funcionalidades

- CRUD de pacientes com busca agrupada por nome, CPF ou CNS e histórico
  completo de atendimentos.
- Registro de atendimentos vinculado a cada paciente, com paginação e
  busca livre.
- Painel gerencial (TI) somente leitura: atendimentos de hoje e do plantão,
  mês contra o mesmo período do mês anterior, movimento por hora, perfil
  (sexo, faixa etária, bairro, cidade, procedência) e qualidade do cadastro.
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

Cada parte tem seu próprio ambiente: `backend/.venv`, `frontend/node_modules`
e, nos notebooks do faturamento, `bpa/.venv` (criado pelo `bpa/instalar.ps1`).

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

### BPA (em cada notebook do faturamento)

O BPA roda **local** em cada notebook, ao lado do Firebird e do BPA
Magnético (offline). Um script instala e atualiza tudo:

```powershell
powershell -ExecutionPolicy Bypass -File bpa\instalar.ps1
```

Ele cria `bpa\.venv`, completa o `bpa\.env` com as credenciais do Firebird
(copiadas do antigo `dashboard\.env`, se existir) e registra a tarefa
`HMPCF-BPA`, que liga o BPA sozinho ao entrar no Windows. Rodar de novo =
atualizar.

---

## Configuração

Credenciais reais nunca são commitadas — `.env` está coberto em todo
lugar pelo `.gitignore` (`.env`, `**/.env`). Copie o `.env.example`
correspondente em cada pasta e preencha com valores reais.

O `bpa/app.py` carrega os três `.env`, nesta ordem (o primeiro valor
encontrado vale): `bpa/.env` → `dashboard/.env` → `backend/.env`.

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

### `bpa/.env` — Firebird e ajustes do notebook

| Variável | Padrão | Descrição |
|---|---|---|
| `FIREBIRD_PATH` | `C:\BPA\BPAMAG.GDB` | Base Firebird local do BPA Magnético |
| `FIREBIRD_USER` / `FIREBIRD_PASSWORD` | — | Credenciais do Firebird |
| `POSTGRES_HOST` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | — | Acesso **só leitura** ao servidor (usuário `bpa_leitura`) |
| `BPA_LOTES_DIR` | `bpa/bpa_lotes` | Lotes `.txt` de digitação diária |
| `BPA_SAIDA_DIR` | *(vazio → `~/Downloads`)* | Pasta de saída do arquivo BPA-I |
| `BPA_ORIGENS_PERMITIDAS` | `http://192.168.1.29:8001,...` | Quem pode chamar este BPA pelo navegador (o sistema do hospital) |

---

## Como Rodar

### Servidor (produção)

Tudo sobe sozinho com o Windows, sem janela:

| O quê | Como |
|---|---|
| Sistema (backend + telas, porta 8001) | serviço `HMPCF-Backend-Svc` (nssm) — religa sozinho se cair |
| PostgreSQL | serviço `postgresql-x64-16` |
| Backup diário 23:00 → Google Drive | tarefa `HMPCF-Backup-Diario` (`scripts\servidor\backup_postgres.bat`) |

Acesso: `http://192.168.1.29:8001`. O terminal da recepção entra sozinho
(auto-login local); os outros PCs usam login e senha.

### Desenvolvimento

```bash
cd backend  && .venv\Scripts\uvicorn app.main:app --reload --port 8001
cd frontend && npm run dev      # proxy /api -> backend
```

### BPA (notebooks do faturamento)

As telas ficam na aba **BPA** do sistema (perfil faturamento): Digitação
(médicos), Enfermeiros, Nutrição do mês, Migração, Conferência e Buscar
prontuário. Quem faz
o trabalho é o BPA local do notebook, que liga sozinho no logon (tarefa
`HMPCF-BPA`) em `http://localhost:8503` e só aceita chamadas do sistema do
hospital. Na primeira abertura do dia ele migra sozinho pro Firebird os
pacientes atendidos nos últimos 40 dias (resultado em `bpa/migracao_auto.json`).
Os lotes de digitação (`bpa_lotes/DD-MM-AAAA.txt`) são copiados sozinhos
para o servidor (tabela `bpa_lotes_backup`) a cada alteração e entram no
backup diário que vai pro Google Drive. Restaurar os de um notebook:
`bpa\.venv\Scripts\python bpa\ferramentas\restaurar_lotes.py <NOTEBOOK>`.
A Nutrição lê a planilha do mês (DADOS NUTRIÇÃO.xlsx, uma aba por mês) e
gera um arquivo só, `BPA_NUTRICAO_<AAAAMM>.txt`, com as nutricionistas e
todos os dias; as regras da planilha estão em `bpa/nutricao.py`.
Manual: `bpa\iniciar.bat` (com console) ou o atalho `bpa\start_bpa.vbs`.

---

## Estrutura de Pastas

```
📦 HMPCF-Automation-System
 ┣ 📂 backend/              # FastAPI — API + serve as telas (porta 8001)
 ┃  ┣ 📂 app/               # api → services → repositories → models
 ┃  ┣ 📂 scripts/           # gerenciar usuários, diagnósticos, criação de tabelas
 ┃  ┗ 📂 tests/             # pytest
 ┣ 📂 frontend/             # React + Vite — todas as telas (menu por perfil)
 ┣ 📂 bpa/                  # BPA local dos notebooks (Firebird / BPA Magnético)
 ┃  ┣ 📜 instalar.ps1       # instala/atualiza + liga com o Windows
 ┃  ┣ 📜 bpa_gerador.py     # layout BPA-I validado byte a byte (DATASUS)
 ┃  ┣ 📂 ferramentas/       # conferência agendada, layout/checksum, preparo mensal
 ┃  ┗ 📂 tests/
 ┣ 📂 scripts/servidor/     # backup (+ criptografia e nuvem), instalador do servidor
 ┣ 📂 docs/                 # documentação viva (+ historico/ com registros datados)
 ┗ 📂 legado/               # o que saiu de uso: dashboard Streamlit, lançadores antigos, scripts de uso único
```

---

## API (Backend)

Prefixo base: `/api/v1`. Documentação interativa só fora de produção
(`http://localhost:8001/docs`). Toda rota exige sessão, exceto `/health` e
`/auth/login`; as marcadas **TI** recusam outros perfis (403).

| Grupo | Rotas principais |
|---|---|
| `auth` | `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` · `POST /auth/change-password` |
| `pacientes` | `GET /pacientes` (busca `q`) · `GET /pacientes/busca` (CPF/CNS) · `GET/PUT /pacientes/{id}` · `POST /pacientes` · `DELETE /pacientes/{id}` **TI** |
| `recepcao` | `GET /recepcao` · `GET /recepcao/recentes` · `GET /recepcao/pacientes/agrupado` · `GET /recepcao/paciente/{id}` · `GET /recepcao/planilha` (mês) · `GET /recepcao/planilha/plantao` · `GET/PUT /recepcao/{id}` · `POST /recepcao` · `DELETE /recepcao/{id}/repetido` (só duplicata real, até 15 min) · `DELETE /recepcao/{id}` **TI** |
| `ti` | `GET/POST /ti/usuarios` · `PATCH /ti/usuarios/{id}/senha` · `PATCH /ti/usuarios/{id}/ativo` · `DELETE /ti/atendimentos/{id}` · `GET /ti/painel` — tudo **TI** |
| `auditoria` | `GET /auditoria` (filtros por recurso, ação, usuário, datas) **TI** |
| `terminal` | `POST /terminal/start` · `POST /terminal/ping` |
| infra | `GET /health` — sem sessão, sem dados sensíveis |

---

## Banco de Dados

PostgreSQL 16 como única fonte de verdade (banco `hmpcf`, fuso
`America/Sao_Paulo`). Hoje as tabelas novas são criadas por scripts em
`backend/scripts/` (`criar_tabelas_auth.py`, `criar_tabela_auditoria.py`,
`adicionar_coluna_sem_documento.py`) — migrações versionadas (Alembic) estão
no plano de organização.

---

## Testes

```bash
cd backend && .venv\Scripts\python -m pytest tests -q   # usa o banco hmpcf_test, nunca o de produção
cd bpa     && .venv\Scripts\python -m pytest tests -q
```

Rodam também no GitHub Actions a cada push. O frontend ainda não tem suíte
automatizada.

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

- **Login por sessão (cookie httpOnly) e perfis** — recepção, faturamento e
  TI; ações só da TI (excluir, usuários, auditoria, painel) são barradas no
  servidor. O terminal fixo da recepção entra sozinho apenas pelo próprio
  PC (auto-login local). Toda escrita fica na auditoria.
- **Banco fechado pra rede** — `postgres` só local; pela rede só o usuário
  `bpa_leitura`, somente leitura.
- **Segredos vivem só em arquivos `.env`** (nunca em scripts ou docs
  versionados) — ao gerar uma senha nova, evite caracteres delimitadores
  de URL (`@ : / ? #`) em strings de conexão, ou garanta que o código
  faça URL-encode antes (o backend já faz isso pro PostgreSQL).
- **Dados sensíveis** (CPF, CNS, endereço, dados de saúde) — evite logar
  esses valores em texto puro em scripts de importação/migração; prefira
  logar só identificadores internos em caso de erro.
- **Backups** (`scripts/servidor/backup_postgres.bat`) são criptografados
  (AES) antes de sair da máquina; ficam 30 dias no servidor e vão pro
  Google Drive.

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
