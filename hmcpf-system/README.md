# HMPCF System v2

Sistema corporativo de automação hospitalar.

## Stack

| Camada | Tecnologia | Porta |
|--------|-----------|-------|
| Backend | FastAPI (Python) | `8000` |
| Frontend | React + Vite | `5173` |
| Desktop | Tauri (Rust) | — |

## Arquitetura

```
hmcpf-system/
├── backend/                  # ★ Backend FastAPI
│   ├── app/
│   │   ├── api/v1/           # REST endpoints (health, bpa, reports, recepcao)
│   │   ├── core/             # Config, logging, exceptions
│   │   ├── services/         # Business logic
│   │   ├── automations/      # Módulos de automação
│   │   ├── modules/          # Domínios (recepção, BPA, relatórios)
│   │   ├── models/           # SQLAlchemy models
│   │   ├── database/         # Sessão e conexão
│   │   └── utils/            # Helpers
│   ├── requirements.txt
│   └── .env                  # Config (host, porta, db, cors)
│
├── frontend/                 # ★ Frontend React
│   ├── src/
│   │   ├── components/       # Componentes reutilizáveis
│   │   ├── pages/            # Páginas (Recepcao, BPA, Reports)
│   │   ├── layouts/          # Layouts de página
│   │   ├── services/         # API client (axios)
│   │   ├── hooks/            # Custom hooks
│   │   ├── contexts/         # React contexts
│   │   └── styles/           # Temas e variáveis CSS
│   ├── src-tauri/            # ★ Tauri desktop shell
│   │   ├── src/main.rs       # Entrypoint (windows subsystem)
│   │   ├── src/lib.rs        # App Tauri
│   │   ├── tauri.conf.json   # Config Tauri (janela, build, dev)
│   │   └── Cargo.toml        # Dependências Rust
│   ├── package.json
│   └── vite.config.js        # Proxy /api → backend:8000
│
├── scripts/                  # Scripts de desenvolvimento
│   ├── start-backend.ps1     # Só o backend
│   ├── start-dev.ps1         # Backend + Vite (navegador)
│   ├── start-tauri.ps1       # Backend + Tauri (desktop)
│   └── start-backend-and-vite.ps1  # Usado internamente pelo Tauri
│
├── desktop/                  # (legado) Pasta antiga do Tauri
├── docs/                     # Documentação
└── README.md
```

### Comunicação frontend → backend

```
React (axios)  →  Vite proxy (/api → 127.0.0.1:8000)  →  FastAPI
```

O Vite faz proxy de todas as requisições `/api/*` para o backend.
Isso elimina problemas de CORS em desenvolvimento.

### Comunicação Tauri → frontend

```
Tauri (Rust webview)  →  devUrl: http://localhost:5173
```

Em produção o Tauri empacota o build estático (`frontend/dist/`).

## Instalação

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Desenvolvimento

### Apenas frontend no navegador (backend separado)

```bash
# Terminal 1 — Backend
cd backend
python -m app.main

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### Frontend + Backend juntos (navegador)

```bash
.\scripts\start-dev.ps1
```

Abre duas janelas: uma para o backend (FastAPI) e outra para o Vite.
Acesse http://localhost:5173.

### Desktop + Backend juntos (Tauri)

```bash
.\scripts\start-tauri.ps1
```

Ou pelo npm:

```bash
cd frontend
npm run tauri:dev:full
```

### Apenas `npx tauri dev` (já sobe a API)

O comando `npx tauri dev` agora já inicia o backend automaticamente
através do `beforeDevCommand` no `tauri.conf.json`.

```bash
cd frontend
npx tauri dev    # ← já sobe backend + vite + janela desktop
```

### Atalhos no npm (dentro de `frontend/`)

| Comando | O que faz |
|---------|-----------|
| `npm run dev` | Só Vite (backend precisa rodar separado) |
| `npm run dev:full` | Backend + Vite |
| `npm run tauri:dev` | Só Tauri (backend precisa rodar separado) |
| `npm run tauri:dev:full` | Backend + Tauri |
| `npm run backend` | Só backend em janela separada |

## Processos necessários em desenvolvimento

| Processo | Onde roda | Porta | Iniciado por |
|----------|-----------|-------|-------------|
| FastAPI | `backend/app/main.py` | `8000` | Scripts ou manual |
| Vite dev server | `frontend/` | `5173` | Scripts ou manual |
| Tauri (webview) | `frontend/src-tauri/` | — | `npm run tauri:dev` |

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/health` | Healthcheck |
| GET | `/api/v1/bpa/` | BPA |
| GET | `/api/v1/reports/` | Relatórios |
| GET/POST | `/api/v1/pacientes` | CRUD pacientes |

## Licença

Uso interno — HMPCF
