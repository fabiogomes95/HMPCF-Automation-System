# Arquitetura

Visão de como o sistema é montado. Operação e instalação: `README.pt-BR.md`;
servidor do zero: `docs/RECUPERACAO_SERVIDOR.md`.

---

## Peças

| Peça | Onde | O que é |
|---|---|---|
| `backend/` | servidor | FastAPI async; API em `/api/v1` e as telas compiladas (`frontend/dist`) na mesma porta 8001 |
| `frontend/` | servidor | React/Vite; um app só com menu por perfil. Gera também as telas do BPA local (`npm run build:bpa` → `bpa/ui`) |
| `bpa/` | cada notebook do faturamento | FastAPI síncrono em `127.0.0.1:8503`; fala com o Firebird do BPA Magnético e lê o PostgreSQL do servidor |
| `scripts/servidor/` | servidor | backup diário (serviço próprio), criptografia e cópia pra nuvem |
| PostgreSQL 16 | servidor | fonte única de verdade (banco `hmpcf`) |

---

## Backend (`backend/app`)

```
api/v1/endpoints/   rotas finas: validam entrada, injetam sessão/usuário, chamam o service
services/           regras de negócio; lançam exceções de domínio (nunca HTTPException)
repositories/       consultas SQLAlchemy async; flush/refresh, nunca commit
models/             tabelas (SQLAlchemy 2, Mapped[]) — espelham o banco de produção
schemas/            Pydantic v2 (Create / Update / Response)
core/               config (pydantic-settings, lê .env) e exceções
database/           engine async, get_db() (um commit por requisição)
```

Fluxo: **endpoint → service → repository → PostgreSQL**. O service recebe a
sessão e instancia o repository com ela (mesma transação); o `get_db()` faz o
commit no fim da requisição ou o rollback se der erro.

**Dependências anotadas** (`api/deps.py`): `DBSession`, `CurrentUser` (sessão
válida; auto-login só no acesso local do terminal da recepção quando
`AUTO_LOGIN_LOCAL=true`) e `TIUser` (403 para quem não é TI).

**Exceções de domínio** (`core/exceptions.py`) viram HTTP em `main.py`:

| Exceção | HTTP |
|---|---|
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `BusinessRuleError`, `ValidationError` | 422 |
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |

Resposta de erro: `{"error": "ConflictError", "message": "..."}`. Rota
`/api/*` inexistente devolve 404 JSON (nunca o `index.html` das telas).

**Auditoria**: toda escrita (pacientes, atendimentos, usuários) grava em
`logs_auditoria` quem fez, o quê e quais campos mudaram — nunca senhas.

**Painel** (`services/painel_service.py`): só agregados (contagens, médias,
faixas), nenhum nome/CPF sai; inclui a saúde do backup
(`services/backup_status.py`, lê `C:\HMPCF\backups`).

### Banco e Alembic

- App: `postgresql+asyncpg://` · Alembic e scripts: `postgresql+psycopg2://`.
- Esquema versionado em `backend/migrations/` (Alembic). A `0001` é o esquema
  de produção de 24/09/2026 — o banco foi só marcado (`stamp`), nunca recriado.
  Os modelos têm os **mesmos nomes** de índices/constraints da produção, então
  `alembic check` mostra zero diferença.
- Regra: mudou um modelo → `alembic revision --autogenerate` → revisar o
  arquivo → backup → `alembic upgrade head`. Nada de `ALTER TABLE` à mão.
- Desfazer a `0001` é bloqueado (apagaria o banco).

---

## BPA local (`bpa/`)

```
bpa_local/
  main.py        app FastAPI: lifespan (cache, migração do dia, backup dos lotes),
                 filtro de origem, /api/status, telas em /ui/
  config.py      carrega bpa/.env (e backend/.env no servidor) ANTES do domínio
  cache.py       pacientes (CADCNS) e profissionais (CADMED) do Firebird em memória
  api/rotas.py   rotas finas → services
  services/      digitacao, geracao, producao (conferência), migracao (+ _auto),
                 nutricao, backup_lotes
bpa_gerador.py   domínio: layout BPA-I (DATASUS, validado byte a byte), folha/sequência,
                 leitura dos lotes, acesso ao Firebird
nutricao.py      leitura da planilha da nutrição (regras combinadas com o faturamento)
conferencia.py   lote digitado x produção importada (S_PRD)
```

- **Rotas `def` (não async)**: Firebird e psycopg2 bloqueiam; o FastAPI roda
  cada chamada numa thread.
- **Quem pode chamar**: só as telas do sistema do hospital
  (`BPA_ORIGENS_PERMITIDAS`) e a própria página local; qualquer outro site
  aberto no notebook leva 403 (CORS + *Private Network Access*).
- **Dados**: lê o PostgreSQL como `bpa_leitura`; escreve no Firebird local
  (`CADCNS` na migração, `S_PRD` só no "reenviar" da Conferência). Os lotes
  `DD-MM-AAAA.txt` ficam em `C:\BPA\bpa_lotes` e são copiados pro servidor
  (tabela `bpa_lotes_backup`) a cada alteração.
- **Regras fixas do BPA-I**: SUS/CNS nunca vai no arquivo; paciente sem CPF
  entra pelo ID do cadastro e sai com `prd_possui_cpf_cns = "s"`; folha e
  sequência continuam a produção real do profissional no mês (conta o `S_PRD`).
- **Processos em lote nunca escrevem nos lotes de digitação** (incidente de
  julho/2026) — a nutrição, por exemplo, gera o arquivo direto da planilha.

---

## Frontend (`frontend/src`)

- `App.jsx`: login, menu por perfil (`TELAS` + primeira aba por papel) e troca
  de tela.
- `services/api.js` (axios, servidor) · `services/bpaLocal.js` (fetch pro
  `localhost:8503`, com tempo limite e erro "BPA desligado").
- `pages/` uma pasta/arquivo por tela; `pages/bpa/` as telas do BPA, usadas
  tanto dentro do sistema quanto em `localhost:8503/ui/`.

---

## Serviços e processos

| Onde | Nome | Como |
|---|---|---|
| servidor | `HMPCF-Backend-Svc` | nssm → `uvicorn app.main:app --port 8001` (LocalSystem) |
| servidor | `HMPCF-Backup-Svc` | nssm → `scripts/servidor/agendador_backup.py` (23:00) |
| servidor | `postgresql-x64-16` | serviço do PostgreSQL |
| notebooks | tarefa `HMPCF-BPA` | ao entrar no Windows → `bpa/executar.py` (sem janela) |

O backup não usa o Agendador de Tarefas do Windows desde 24/09/2026 (ele parou
de executar no servidor); o serviço também cobre o PC desligado às 23:00
(faz ao ligar se o último tiver mais de 26 h).

---

Decisões e marcos: `docs/HISTORICO.md` · pendências: `docs/PENDENCIAS.md`.
