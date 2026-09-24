# HMPCF Automation System

🇺🇸 [English summary](README.md) · este arquivo é a documentação principal

> Sistema do Hospital Municipal Pres. Café Filho (Extremoz/RN): recepção
> digital, painel gerencial e faturamento SUS (BPA), num sistema só.

**FastAPI + PostgreSQL 16 + React/Vite** no servidor da recepção, com menu por
perfil (recepção, faturamento, TI), e o **BPA local** em cada notebook do
faturamento, ao lado do Firebird e do BPA Magnético (que continuam offline).

---

## Módulos

| Módulo | O que faz | Onde roda |
|---|---|---|
| **Recepção** | cadastro de pacientes, atendimento com boletim A4, histórico, planilha mensal por plantão, correção | servidor (`backend/` + `frontend/`) |
| **Painel** (TI) | atendimentos do dia/plantão/mês, movimento por hora, perfil, qualidade do cadastro e **saúde do backup** — só números agregados | servidor, `GET /api/v1/ti/painel` |
| **Auditoria e usuários** (TI) | quem criou/editou/apagou o quê; gestão de contas | servidor |
| **Entradas** (faturamento, TI) | em que dias o paciente deu entrada e quantas vezes — no sistema e nas **planilhas manuais desde ago/2021** — pra achar o boletim impresso (guardado por data) | servidor, `GET /api/v1/entradas` |
| **BPA** (faturamento) | Digitação (médicos), Enfermeiros, **Nutrição do mês**, Migração pro Firebird, Conferência, Buscar prontuário → arquivos BPA-I pra importar no BPA Magnético | telas no servidor, trabalho no notebook (`bpa/`) |

Perfis: **recepção** (Recepção, Histórico, Planilha) · **faturamento** (BPA —
abre nela —, Entradas, Recepção, Histórico, Planilha, Correção) · **TI** (tudo).

---

## Como funciona

```
 Notebooks do faturamento (x2)                 Servidor (PC da recepção, 192.168.1.29)
 ┌──────────────────────────────┐              ┌──────────────────────────────────────┐
 │ Chrome ── telas do sistema ──┼── :8001 ────▶│ HMPCF-Backend-Svc (FastAPI + telas)  │
 │   │                          │              │   └─ PostgreSQL 16 (hmpcf)           │
 │   └─ localhost:8503          │              │ HMPCF-Backup-Svc (backup 23:00)      │
 │      BPA local (FastAPI) ────┼── :5432 ────▶│   └─ C:\HMPCF\backups_nuvem → Drive  │
 │        └─ Firebird BPAMAG    │ bpa_leitura  └──────────────────────────────────────┘
 │           + BPA Magnético    │
 └──────────────────────────────┘
```

- O **navegador** do notebook carrega as telas do servidor e chama o BPA local
  (`localhost:8503`), que só aceita pedidos vindos do sistema do hospital.
- O **BPA local** lê pacientes/atendimentos do servidor com o usuário
  `bpa_leitura` (só leitura), grava no Firebird do próprio notebook e manda
  uma cópia dos lotes de digitação pro servidor.
- Na primeira abertura do dia ele **migra sozinho** pro Firebird os pacientes
  dos últimos 40 dias.

Detalhes das camadas: [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

---

## Stack

| Parte | Stack |
|---|---|
| Backend | Python 3.12+ · FastAPI · SQLAlchemy 2 (async) · asyncpg · Pydantic v2 · Alembic |
| Frontend | React 18 · Vite 5 · axios |
| BPA local | Python 3.12+ · FastAPI · firebirdsql · psycopg2 · openpyxl |
| Banco | PostgreSQL 16 nativo no Windows (sem Docker) |
| Serviços | nssm (`HMPCF-Backend-Svc`, `HMPCF-Backup-Svc`) · Tarefa `HMPCF-BPA` nos notebooks |
| Testes | pytest (backend com Postgres, BPA com Firebird simulado) · GitHub Actions a cada push |

---

## Operação no dia a dia

### Servidor

| O quê | Como |
|---|---|
| Sistema (porta 8001) | serviço `HMPCF-Backend-Svc` — liga com o Windows e religa se cair |
| Banco | serviço `postgresql-x64-16` |
| Backup | serviço `HMPCF-Backup-Svc`: todo dia às 23:00 (ou na hora, criando `C:\HMPCF\backups\RODAR_AGORA`) → `pg_dump` → criptografia AES → `C:\HMPCF\backups` (30 dias) + `C:\HMPCF\backups_nuvem`, que o Google Drive sincroniza |
| Conferir o backup | faixa no topo da aba **Painel** (vermelha se atrasar ou não chegar na nuvem) |

Acesso: `http://192.168.1.29:8001`. O terminal da recepção entra sozinho
(auto-login local); os outros PCs usam login e senha.

**Atualizar o servidor:** `git pull`, `npm run build` em `frontend/` (telas —
valem na hora, F5) e, se mudou o backend, reiniciar o `HMPCF-Backend-Svc`.
Mudou modelo do banco: `alembic upgrade head` antes de reiniciar.

> Reiniciar o backend às vezes trava em *StopPending* (nssm). Nesse caso:
> finalizar o processo do nssm do serviço e `Start-Service HMPCF-Backend-Svc`.

### Notebooks do BPA

```powershell
cd C:\HMPCF-Automation-System
git pull
powershell -ExecutionPolicy Bypass -File bpa\instalar.ps1
```

Instala/atualiza o BPA, confere o `bpa\.env`, liga com o Windows e cria o
atalho **HMPCF - BPA**. Detalhes: [`bpa/README.md`](bpa/README.md).

- Lotes de digitação: `C:\BPA\bpa_lotes\DD-MM-AAAA.txt` (cópia no servidor;
  restaurar: `bpa\ferramentas\restaurar_lotes.py`).
- Arquivos pra importar no BPA Magnético: `BPA_MEDICOS_<data>.txt`,
  `BPA_ENFERMEIROS_<data>.txt`, `BPA_NUTRICAO_<AAAAMM>.txt`.
- O **SUS/CNS nunca vai no BPA-I**; paciente sem CPF vai como *sem documento*.

### Planilhas manuais (aba Entradas)

As planilhas da recepção de antes do sistema (ago/2021 em diante) ficam em
`C:\HMPCF\planilhas_manuais\` no servidor — **fora do repositório** (têm dados
de pacientes; `*.xlsx` está no `.gitignore`). Chegou planilha nova ou corrigida:
copie pra essa pasta e rode, na pasta `backend`:

```
.venv\Scripts\python scripts\importar_planilhas_recepcao.py            # recarrega tudo
.venv\Scripts\python scripts\importar_planilhas_recepcao.py --simular  # só confere a leitura
```

Regras de leitura (dia pelas linhas de plantão, CPF em qualquer coluna, erros de
digitação, cópias): `backend/app/importacao/planilhas_recepcao.py`.

---

## Instalação (desenvolvimento)

```bash
cd backend  && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
copy backend\.env.example backend\.env        # POSTGRES_PASSWORD
cd frontend && npm install
```

```bash
cd backend  && .venv\Scripts\uvicorn app.main:app --reload --port 8001
cd frontend && npm run dev          # telas com proxy /api -> backend
cd frontend && npm run build:bpa    # telas do BPA local (bpa/ui, versionado: os notebooks não têm Node)
```

Servidor novo ou restauração depois de pane:
[`docs/RECUPERACAO_SERVIDOR.md`](docs/RECUPERACAO_SERVIDOR.md).

---

## Configuração

Segredos só em `.env` (fora do git). Modelos: `backend/.env.example` e
`bpa/.env.example`.

| Arquivo | Principais variáveis |
|---|---|
| `backend/.env` | `POSTGRES_*`, `ENVIRONMENT=production` (esconde `/docs`), `AUTO_LOGIN_LOCAL` (só no terminal da recepção), `BACKUP_DIR`, `TEST_POSTGRES_DB=hmpcf_test` |
| `bpa/.env` | `FIREBIRD_*`, `POSTGRES_*` (usuário `bpa_leitura`), `BPA_LOTES_DIR=C:\BPA\bpa_lotes`, `BPA_SAIDA_DIR` |
| `scripts/servidor/.backup_passphrase` | senha de criptografia do backup — **guardar também fora do servidor** |

---

## Banco de dados

PostgreSQL 16, banco `hmpcf`, fuso `America/Sao_Paulo`. O esquema é versionado
com **Alembic** (`backend/migrations/`; a versão `0001` é o esquema de
produção de 24/09/2026). Na pasta `backend`:

```
.venv\Scripts\python -m alembic revision --autogenerate -m "o que mudou"   # depois de mudar um modelo
.venv\Scripts\python -m alembic upgrade head                              # aplica (faça backup antes)
.venv\Scripts\python -m alembic check                                     # banco == modelos?
```

---

## API

Prefixo `/api/v1`; documentação interativa só fora de produção
(`/docs`). Tudo exige sessão, menos `/health` e `/auth/login`; **TI** = só
perfil TI (403 para os outros).

| Grupo | Rotas |
|---|---|
| `auth` | `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` · `POST /auth/change-password` |
| `pacientes` | `GET /pacientes` (`q`) · `GET /pacientes/busca` · `GET/PUT /pacientes/{id}` · `POST /pacientes` · `DELETE /pacientes/{id}` **TI** |
| `recepcao` | `GET /recepcao` · `/recentes` · `/pacientes/agrupado` · `/paciente/{id}` · `/planilha` · `/planilha/plantao` · `GET/PUT /recepcao/{id}` · `POST /recepcao` · `DELETE /recepcao/{id}/repetido` (duplicata real, até 15 min) · `DELETE /recepcao/{id}` **TI** |
| `ti` | `GET/POST /ti/usuarios` · `PATCH /ti/usuarios/{id}/senha` · `PATCH /ti/usuarios/{id}/ativo` · `DELETE /ti/atendimentos/{id}` · `GET /ti/painel` — **TI** |
| `entradas` | `GET /entradas?q=&fonte=ambos\|sistema\|planilhas` · `GET /entradas/planilhas` — faturamento e TI |
| `auditoria` | `GET /auditoria` **TI** |
| `terminal` | `POST /terminal/start` · `POST /terminal/ping` |
| infra | `GET /health` |

O BPA local (`localhost:8503/api/...`) tem a própria API, usada só pelas telas
do BPA — rotas em `bpa/bpa_local/api/rotas.py`.

---

## Testes

```bash
cd backend && .venv\Scripts\python -m pytest -q    # banco hmpcf_test, nunca o de produção
cd bpa     && .venv\Scripts\python -m pytest -q    # Firebird simulado
```

Rodam no GitHub Actions a cada push. O frontend ainda não tem suíte.

---

## Estrutura

```
backend/            API + telas compiladas (porta 8001)
  app/              api → services → repositories → models
  migrations/       Alembic
  scripts/          gerenciar usuários, diagnósticos
  tests/
frontend/           React + Vite — todas as telas (menu por perfil)
bpa/                BPA local dos notebooks
  bpa_local/        FastAPI: api → services (+ cache do Firebird)
  bpa_gerador.py    layout BPA-I (DATASUS), validado byte a byte
  nutricao.py       leitura da planilha da nutrição
  conferencia.py    digitado x importado no BPA Magnético
  ui/               telas do BPA compiladas (versionado)
  instalar.ps1      instala/atualiza + liga com o Windows + atalho
scripts/servidor/   backup (serviço, criptografia, nuvem)
docs/               arquitetura, recuperação do servidor, pendências, histórico
legado/             tudo que saiu de uso, só como referência
```

---

## Segurança

- Rede local do hospital, não exposto à internet.
- Sessão por cookie httpOnly e perfis; ações de TI barradas no servidor; toda
  escrita vai pra auditoria.
- PostgreSQL: `postgres` só local; pela rede só `bpa_leitura` (leitura +
  gravar a cópia dos lotes).
- O BPA local só aceita chamadas do sistema do hospital (origem conferida).
- Backups criptografados (AES) antes de sair da máquina.
- CPF/CNS nunca vão pro git (lotes e planilhas ficam fora do repositório, que
  é público).

---

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação em
produção sem autorização explícita do autor.
