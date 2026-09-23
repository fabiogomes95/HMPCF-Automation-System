# HMPCF Automation System

🇧🇷 **Full documentation in Portuguese: [README.pt-BR.md](README.pt-BR.md)** — the
single source of truth for installation, configuration, API and operations.
This page is a short English summary.

> Hospital automation system for digital reception, management dashboard and
> SUS/BPA billing. Built for Hospital Municipal Pres. Café Filho — Extremoz,
> Rio Grande do Norte, Brazil.

---

## What it is

| Part | Where it runs | Stack |
|---|---|---|
| **Hospital system** — reception intake (A4 form), history, monthly shift sheet, corrections, IT dashboard, audit log, user management | Server (Windows service, port 8001) | FastAPI · PostgreSQL 16 · React/Vite |
| **BPA billing** — daily batch entry, BPA-I positional file (DATASUS layout, byte-validated), PostgreSQL → Firebird patient migration | Locally on each billing laptop, next to the offline BPA Magnético app and its Firebird database | Python (being moved to FastAPI) · Firebird |

One web interface with a role-based menu:

| Role | Sees |
|---|---|
| `recepcao` | Reception, History, Sheet — the fixed reception terminal logs in automatically |
| `faturamento` | Reception, History, Sheet, Corrections (add/edit only) and the laptop's local BPA |
| `ti` | Everything, including Dashboard, Audit and Users |

## Highlights

- Session login (httpOnly cookie) with server-side role checks; every write is audited.
- Database closed to the network: only a read-only user reaches it remotely.
- Encrypted nightly backup copied off-machine (Google Drive), restore-tested.
- Management dashboard with aggregates only — no personal data leaves the API.
- Tests (pytest) for backend and BPA run on every push.

## Repository layout

```
backend/            FastAPI app (api → services → repositories → models) + tests
frontend/           React/Vite UI served by the backend
bpa/                local BPA service for the billing laptops (+ installer, tools, tests)
scripts/servidor/   server backup (encrypted, cloud copy) and installer
docs/               living documentation (+ historico/ for dated records)
legado/             everything retired (old Streamlit dashboard, launchers, one-off scripts)
```

---

## License

Copyright (c) 2026 Fabio Gomes. All rights reserved.

Published for study, technical demonstration, and portfolio purposes.
Commercial, institutional, or production use is not permitted without the
author's explicit authorization.
