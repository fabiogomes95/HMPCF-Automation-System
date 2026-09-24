# HMPCF Automation System

🇧🇷 **Main documentation in Portuguese: [README.pt-BR.md](README.pt-BR.md)**. This
page is a short English summary.

> Hospital system for Hospital Municipal Pres. Café Filho (Extremoz, Rio
> Grande do Norte, Brazil): digital reception, management dashboard and SUS
> billing (BPA), in a single application.

---

## What it is

| Part | Where it runs | Stack |
|---|---|---|
| **Hospital system**: reception intake (A4 form), history, monthly shift sheet, corrections, IT dashboard (incl. backup health), audit log, user management | Server (Windows services via nssm, port 8001) | FastAPI · PostgreSQL 16 · Alembic · React/Vite |
| **BPA billing**: daily entry for doctors/nurses, monthly nutrition file from a spreadsheet, BPA-I positional file (DATASUS layout, byte-validated), PostgreSQL → Firebird patient migration, reconciliation | UI served by the server; the work runs on each billing laptop, next to the offline BPA Magnético app and its Firebird database | FastAPI · Firebird |

One web interface with a role-based menu:

| Role | Sees |
|---|---|
| `recepcao` | Reception, History, Sheet (the fixed reception terminal logs in automatically) |
| `faturamento` | BPA (opens first), Reception, History, Sheet, Corrections |
| `ti` | Everything, including Dashboard, Audit and Users |

## Highlights

- Session login (httpOnly cookie) with server-side role checks; every write is audited.
- Database closed to the network: only a read-only user reaches it remotely.
- The laptop's local BPA service only accepts calls from the hospital system.
- Encrypted nightly backup (own Windows service) copied off-machine to Google
  Drive; restore-tested; health shown on the dashboard.
- Schema versioned with Alembic; disaster-recovery guide in `docs/`.
- Tests (pytest) for backend and BPA run on every push (GitHub Actions).

## Repository layout

```
backend/            FastAPI app (api → services → repositories → models), Alembic, tests
frontend/           React/Vite UI served by the backend
bpa/                local BPA service for the billing laptops (+ installer, tests)
scripts/servidor/   server backup (service, encryption, cloud copy)
docs/               architecture, server recovery, backlog, history
legado/             everything retired, kept for reference only
```

---

## License

Copyright (c) 2026 Fabio Gomes. All rights reserved.

Published for study, technical demonstration, and portfolio purposes.
Commercial, institutional, or production use is not permitted without the
author's explicit authorization.
