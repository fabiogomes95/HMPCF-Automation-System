# HMPCF System v2

Sistema corporativo de automação hospitalar com arquitetura moderna.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI (Python) |
| Frontend | React + Vite |
| Desktop | Tauri (Rust) |
| Database | SQLite → PostgreSQL |

## Estrutura

```
hmcpf-system/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── core/         # Config, logging, exceptions
│   │   ├── services/     # Business logic
│   │   ├── automations/  # Automation modules
│   │   ├── modules/      # Domain modules (recepção, BPA, relatórios)
│   │   ├── models/       # SQLAlchemy models
│   │   ├── database/     # Session management
│   │   └── utils/        # Helpers
│   ├── requirements.txt
│   └── .env
├── frontend/         # React + Vite SPA
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Route pages
│   │   ├── layouts/      # Page layouts
│   │   ├── services/     # API client (Axios)
│   │   ├── hooks/        # Custom React hooks
│   │   ├── contexts/     # React contexts
│   │   ├── routes/       # Router config
│   │   └── styles/       # CSS variables, theme
│   ├── package.json
│   └── vite.config.js
├── desktop/          # Tauri desktop shell
│   └── tauri/
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

## Instalação

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Desktop (Tauri)

```bash
cd desktop/tauri
cargo tauri dev
```

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/health` | Healthcheck |
| GET | `/api/v1/bpa/` | BPA (placeholder) |
| GET | `/api/v1/reports/` | Relatórios (placeholder) |

## Licença

Uso interno — HMPCF
