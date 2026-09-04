# HMPCF Automation System

🇧🇷 [Leia em português](README.pt-BR.md)

> Hospital automation system for digital reception, a real-time management
> dashboard, and SUS/BPA billing. Built for Hospital Municipal Pres. Café
> Filho — Extremoz, Rio Grande do Norte, Brazil.

Modern stack — **FastAPI + PostgreSQL + React/Vite** for reception, a
**Streamlit** dashboard for coordination/IT, and a standalone **Flask +
Firebird** service dedicated to generating SUS/BPA billing files.

---

## Overview

The system is made up of three independent fronts, all reading the same
PostgreSQL database as the single source of truth:

1. **Digital reception** (`backend/` + `frontend/`) — patient registration
   and visit intake, in production on the reception terminal at the
   hospital.
2. **Management dashboard** (`dashboard/`) — real-time view for
   coordinators and IT: daily history, patient lookup, and manual
   spreadsheet import. Independent process, read-only by default, doesn't
   interfere with reception.
3. **SUS/BPA billing** (`bpa/`) — a separate Flask app that generates the
   positional BPA-I files (one per professional/category, per billing
   period) from PostgreSQL attendance records, migrating data into the
   Firebird database (`BPAMAG.GDB`) required by Brazil's BPA Magnético
   system.

The **legacy system** (`legado/`, Python/Eel/SQLite) was **discontinued on
2026-07-02** — it stays in the repo purely as historical reference and
gets no further maintenance or deploys.

---

## Status

| Module | State |
|--------|-------|
| Digital reception (FastAPI + React) | **In production** |
| Management dashboard (Streamlit) | **In production** |
| SUS/BPA billing (positional file generation) | **In production** |
| Manual spreadsheet import (dedup, shift/timezone correction) | **In production** |
| Auto-start (Scheduled Task + watchdog) | Configured |
| API authentication / authorization | **Not implemented** — designed for the hospital's isolated LAN; see [Security](#security--known-limitations) |
| Automated tests (backend) | 21 tests |
| Automated tests (frontend / dashboard / bpa) | None yet |
| Legacy system (Firebird/Eel) | **Discontinued** — kept for reference only |

---

## Features

- Patient CRUD and grouped search by name, CPF, or CNS with full visit
  history.
- Attendance (visit) records tied to each patient, with pagination and
  free-text search.
- Read-only management dashboard: daily KPIs (volume, sex, age bracket,
  neighborhood), full daily history, and patient lookup across all
  records.
- Manual spreadsheet import (`.tsv`) that diffs against the database and
  imports only what's missing, with deduplication and automatic
  night-shift date correction.
- BPA-I file generation following the official DATASUS 350-character
  positional layout, with continuous sheet/sequence numbering per
  competency.
- PostgreSQL → Firebird migration for the BPA Magnético cadastre
  (`CADCNS`), with CPF validation before migrating.
- Printable A4 attendance form (`boletim`) for the reception desk.

---

## Tech stack

| Component | Stack |
|---|---|
| Backend (reception API) | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · asyncpg · Pydantic v2 · pytest |
| Frontend (reception UI) | React 18.3 · Vite 5.4 · axios |
| Dashboard | Streamlit · pandas · Plotly · SQLAlchemy (sync, psycopg2) |
| BPA billing | Flask · firebirdsql · psycopg2 · pandas/openpyxl |
| Database | PostgreSQL 16 — native install, **not containerized** |
| Legacy (discontinued) | Python · Eel · SQLite |

---

## Prerequisites

- Windows 10/11 (the production target — hospital LAN, 24/7 uptime)
- Python 3.12+
- Node.js 18+ and npm (frontend build only)
- PostgreSQL 16, installed natively (not Docker — see [Database](#database) note)
- Firebird client + a `BPAMAG.GDB` database, for the `bpa/` module only

TODO: pin exact Node.js/npm versions if the project starts using an `.nvmrc` or CI matrix.

---

## Installation

Each app keeps its own virtual environment/dependencies, except `bpa/`,
which reuses `dashboard/`'s (see [How to Run](#how-to-run) below).

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp .env.example .env   # fill in POSTGRES_PASSWORD
```

### Frontend

```bash
cd frontend
npm install
npm run build   # outputs frontend/dist, served by the backend in production
```

### Dashboard (also used to run `bpa/`)

```bash
cd dashboard
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp .env.example .env   # fill in FIREBIRD_* credentials
```

### BPA billing

```bash
cd bpa
cp .env.example .env   # adjust BPA_LOTES_DIR / BPA_SAIDA_DIR for this machine
```

No separate virtual environment — `bpa/app.py` runs on
`dashboard/.venv` (see `bpa/iniciar.bat`). `bpa/requirements.txt` exists
to document what that shared environment needs, in case `bpa/` ever gets
its own venv.

---

## Configuration

Real credentials never get committed — `.env` is covered everywhere by
`.gitignore` (`.env`, `**/.env`). Copy the matching `.env.example` in each
app folder and fill in real values.

`bpa/app.py` loads all three `.env` files, in this order (first value
found wins): `bpa/.env` → `dashboard/.env` → `backend/.env`. `dashboard/db.py`
reads `backend/.env` directly for its (read-only) PostgreSQL connection.

### `backend/.env` — PostgreSQL, API

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `HMPCF` | Display name used in FastAPI's OpenAPI metadata |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` — hides `/docs`, `/redoc`, `/openapi.json` in production |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | — (required) | PostgreSQL password — URL-encoded automatically before building the connection string |
| `POSTGRES_DB` | `hmpcf` | Database name |
| `DATABASE_POOL_SIZE` | `10` | SQLAlchemy async pool size |
| `DATABASE_MAX_OVERFLOW` | `20` | Extra connections allowed on demand |
| `DATABASE_POOL_PRE_PING` | `true` | Tests connections before reuse |
| `CORS_ORIGINS` | `["*"]` | Safe as `["*"]` in production since frontend and backend share an origin on the hospital LAN |
| `TEST_POSTGRES_DB` | `hmpcf_test` | Database used by the pytest suite — never point this at `hmpcf` |

### `dashboard/.env` — Firebird (used by the BPA migration feature)

| Variable | Default | Description |
|---|---|---|
| `FIREBIRD_PATH` | `C:\BPA\BPAMAG.GDB` | Path to the local Firebird database |
| `FIREBIRD_USER` | `SYSDBA` | Firebird user |
| `FIREBIRD_PASSWORD` | — (required) | Firebird password |
| `BPA_LOTES_DIR` | `dashboard/bpa_lotes` (repo-relative) | Folder holding the raw daily `.txt` batch files |
| `BPA_SAIDA_DIR` | *(empty → `~/Downloads`)* | Output folder for the generated BPA-I file |

### `bpa/.env` — per-machine overrides for the Flask app

| Variable | Default | Description |
|---|---|---|
| `BPA_LOTES_DIR` | `bpa/bpa_lotes` (repo-relative, if unset) | Same as above, overridable per machine |
| `BPA_SAIDA_DIR` | *(empty → `~/Downloads`)* | Same as above |
| `POSTGRES_HOST` | inherited from `backend/.env` | Override when running the Flask app on a machine with a different PostgreSQL host |
| `BPA_DIGITACAO_PORT` | `8503` | Port for the Flask app |

---

## How to Run

### Reception (Windows, production)

```bat
INICIAR.bat
```

Starts the backend (`uvicorn`, port 8001 — which also serves the built
frontend from `frontend/dist/`) and opens the browser. Registered as a
Windows Scheduled Task (`HMPCF-Backend`) — starts on boot and auto-restarts
if it goes down (watchdog at `scripts/windows/watchdog_backend.vbs`).

> Two more launchers exist for the same backend
> (`scripts/windows/ABRIR_HMPCF.bat`, `scripts/windows/iniciar_sistema.vbs`)
> — TODO: consolidate into one once it's confirmed, on a test machine,
> which one is actually registered in Task Scheduler on the production PC.

### Reception (development)

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8001
```

```bash
cd frontend
npm run dev
```

Vite's dev server proxies `/api` to `http://desktop-9c4s1co:8001` (see
`frontend/vite.config.js`) — that hostname is the production machine's;
edit the proxy target if you're running the backend somewhere else.

### Management dashboard (Streamlit)

```bash
cd dashboard
.venv\Scripts\streamlit run app.py
```

Runs on `http://localhost:8502` (LAN: `http://<machine-ip>:8502`).
Launcher at `scripts/windows/ABRIR_DASHBOARD.bat`, also registered as its
own Scheduled Task, independent from the backend.

### SUS/BPA billing (Flask)

```bash
cd bpa
..\dashboard\.venv\Scripts\python.exe app.py
```

Runs on `http://localhost:8503`. Requires read access to PostgreSQL
(attendance records) and to the local Firebird database of the BPA
Magnético system. Desktop-shortcut launchers: `bpa/iniciar.bat`,
`bpa/start_bpa.vbs` (silent, no console window — see `bpa/README.md`).

---

## Project Structure

```
📦 HMPCF-Automation-System
 ┣ 📂 backend/                       # FastAPI API — digital reception
 ┃  ┗ 📂 app/
 ┃     ┣ 📜 main.py                  # Entrypoint (lifespan, CORS, exception handlers)
 ┃     ┣ 📂 core/                    # Settings (pydantic-settings) + domain exceptions
 ┃     ┣ 📂 database/                # Async engine, SessionLocal
 ┃     ┣ 📂 models/                  # SQLAlchemy ORM (patients, attendances)
 ┃     ┣ 📂 schemas/                 # Pydantic v2
 ┃     ┣ 📂 repositories/            # Isolated queries
 ┃     ┣ 📂 services/                # Business rules
 ┃     ┗ 📂 api/v1/endpoints/        # pacientes · recepcao · terminal
 ┃  ┗ 📂 tests/                      # 21 tests (pytest)
 ┣ 📂 frontend/                      # React + Vite — reception input terminal
 ┣ 📂 dashboard/                     # Streamlit — management dashboard (IT/coordination)
 ┃  ┣ 📜 app.py                      # KPIs, charts (volume, sex, age, neighborhood)
 ┃  ┣ 📜 db.py                       # Read-only connection + shared helpers
 ┃  ┗ 📂 pages/                      # Daily history · monthly import · patient search
 ┣ 📂 bpa/                           # Flask — BPA-I generation, PG→Firebird migration
 ┃  ┣ 📜 app.py                      # Data entry, BPA-I generation, migration
 ┃  ┣ 📜 bpa_gerador.py              # Core BPA-I logic (layout, checksum, sheet/seq)
 ┃  ┣ 📂 auditoria_mensal/           # Incident-response scripts, actively reused
 ┃  ┗ 📂 legado/                     # Archived one-off/backup files local to bpa/
 ┣ 📂 docs/                          # Living documentation (architecture, deploy, install)
 ┃  ┗ 📂 historico/                  # Point-in-time records (past audits, migrations)
 ┣ 📂 scripts/
 ┃  ┣ 📂 bpa/                        # CLI helpers alongside the Flask app
 ┃  ┣ 📂 importacao/                 # Monthly import pipeline (+ legado/ for one-offs)
 ┃  ┣ 📂 migrations/legado/          # SQLite→PostgreSQL migration, already executed
 ┃  ┗ 📂 windows/                    # Launchers, backup, Scheduled Task registration
 ┣ 📂 legado/                        # Original system — discontinued, kept for reference
 ┃  ┗ 📂 docker-compose/             # Discontinued Docker setup (see NOTA.md)
 ┗ 📜 INICIAR.bat                    # Reception launcher (backend + frontend), production
```

---

## API (Backend)

Base path: `/api/v1`. Interactive docs (non-production only):
`http://localhost:8001/docs`.

### `pacientes`

| Method | Route | Description |
|---|---|---|
| GET | `/pacientes` | List patients (paginated, optional `q` search — name/CPF/CNS) |
| GET | `/pacientes/busca` | Look up a single patient by CPF or CNS (`documento`) |
| GET | `/pacientes/{id}` | Get patient by ID |
| POST | `/pacientes` | Create patient |
| PUT | `/pacientes/{id}` | Update patient |
| DELETE | `/pacientes/{id}` | Delete patient |

### `recepcao`

| Method | Route | Description |
|---|---|---|
| GET | `/recepcao` | List attendances, most recent first (paginated, optional `q`) |
| GET | `/recepcao/pacientes/agrupado` | Grouped search — unique patients with total visit count (`q` required, min 3 chars) |
| GET | `/recepcao/recentes` | Most recent attendances |
| GET | `/recepcao/paciente/{paciente_id}` | Full attendance history for one patient |
| GET | `/recepcao/{id}` | Full detail of one attendance |
| POST | `/recepcao` | Register a new attendance |
| PUT | `/recepcao/{id}` | Update an attendance |
| DELETE | `/recepcao/{id}` | Remove an attendance |

### `terminal`

| Method | Route | Description |
|---|---|---|
| POST | `/terminal/start` | Start a terminal session |
| POST | `/terminal/ping` | Keep-alive ping from the terminal |

### Infra

| Method | Route | Description |
|---|---|---|
| GET | `/health` | Health check — no auth required, no sensitive data |

---

## Database

PostgreSQL is the single source of truth. **TODO**: the docs previously
referenced Alembic-managed migrations, but no `alembic.ini`, `alembic/`
folder, or `alembic` dependency currently exist in this repo — how the
schema is actually created/versioned needs to be confirmed and documented
here (or an Alembic setup added, if that's still the intent).

---

## Testing

```bash
cd backend
pytest tests/ -v
```

21 tests covering `pacientes`, `recepcao`, and `terminal` (backend only —
frontend, dashboard, and `bpa/` have no automated suite yet). Frontend has
Playwright installed as a dev dependency but no spec files exist yet —
TODO if end-to-end coverage is planned.

---

## Deploy

Production runs natively on Windows (no Docker, no containers) on the
hospital's reception PC, over the internal LAN. Full step-by-step guides:

- `docs/DEPLOY_HOSPITAL.md` — general deployment guide
- `docs/INSTALACAO_PC_RECEPCAO.md` — setting up a reception PC from scratch
- `docs/INSTALACAO_BPA_MIGRACAO.md` — installing the BPA app + PG→Firebird migration on a new machine

---

## Security & Known Limitations

This system is designed to run inside the hospital's **isolated local
network**, not exposed to the internet. Notes for anyone deploying or
operating it:

- **No API authentication/authorization yet** — any device with access to
  the backend's LAN can read/write attendance records. Compensate with
  proper network segmentation (Windows firewall profile `Domain`/`Private`,
  never `Public`, and a dedicated VLAN if possible) until auth ships.
- **Secrets live only in `.env` files** (never in versioned scripts or
  docs) — when generating a new password, avoid URL delimiter characters
  (`@ : / ? #`) in connection strings, or make sure the code URL-encodes
  the password first (the backend already does this for PostgreSQL).
- **Sensitive data** (CPF, CNS, address, health data) — avoid logging
  these values in plaintext in import/migration scripts; log internal IDs
  instead when something fails.
- **Backups** (`scripts/windows/backup_postgres.bat`) produce a local
  plaintext dump — pair this with access control on the backup directory
  and rotation (already implemented, 30 days).

Contributions that close these gaps (session auth, basic RBAC, backup
encryption) are welcome.

---

## Legacy System

The original system (`legado/`, Python/Eel/SQLite) was **officially
discontinued on 2026-07-02**. It stays in the repo as historical reference
and documentation fallback only — no deploys, no maintenance. See
`legado/passo_a_passo.md` if you need to understand how it used to operate.

---

## License

Copyright (c) 2026 Fabio Gomes. All rights reserved.

Published for study, technical demonstration, and portfolio purposes.
Commercial, institutional, or production use is not permitted without the
author's explicit authorization.
