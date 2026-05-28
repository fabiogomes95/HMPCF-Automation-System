# Migração HMPCF — Eel → FastAPI + React + Tauri

> Registro da migração do sistema legado (Eel) para a nova arquitetura corporativa.

## Arquitetura Atual (Legado)

```
HMPCF/                          ← sistema em produção (mantido)
├── app_painel.py               ← Eel (Bottle + gevent + WebSocket)
├── app_recepcao.py             ← Eel (Bottle + gevent + WebSocket)
├── web_painel/                 ← HTML/CSS/JS servido por Eel
├── web_recepcao/               ← HTML/CSS/JS servido por Eel
├── main.py                     ← CLI + Update manager
├── analise/                    ← Módulos Python (PDF, consultas, dashboard)
├── automacao/                  ← Automações (RPA, digitação)
├── integracao/                 ← Integrações (Firebird, CSV, BPA)
├── scripts/                    ← Utilitários
└── hmcpf-system/               ← NOVA ARQUITETURA (em construção)
```

## Stack da Nova Arquitetura

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| **Backend** | FastAPI (Python) | API REST, serviços, automações |
| **Frontend** | React + Vite | SPA moderna, tema dark/light |
| **Desktop** | Tauri (Rust) | Empacotamento desktop nativo |
| **Database** | SQLite → PostgreSQL | Persistência escalável |
| **Comunicação** | HTTP REST | Frontend ↔ Backend |

## Estrutura do Novo Sistema

```
hmcpf-system/
├── backend/
│   ├── app/
│   │   ├── api/            ← Rotas REST (v1/health, v1/bpa, v1/reports)
│   │   ├── core/           ← Config, logging, exceptions
│   │   ├── services/       ← Lógica de negócio
│   │   ├── automations/    ← Módulos de automação (base abstrata)
│   │   ├── modules/        ← Domínios: recepcao, bpa, relatorios
│   │   ├── models/         ← Modelos SQLAlchemy
│   │   ├── database/       ← Sessão e base declarativa
│   │   ├── utils/          ← Helpers
│   │   └── main.py         ← Entrypoint FastAPI
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/     ← Sidebar, cards, etc.
│   │   ├── pages/          ← Dashboard, BPA, Reports
│   │   ├── layouts/        ← AppLayout (sidebar + main)
│   │   ├── services/       ← Axios client centralizado
│   │   ├── hooks/          ← useTheme
│   │   ├── contexts/       ← ThemeContext (dark/light)
│   │   ├── routes/         ← React Router config
│   │   └── styles/         ← Variáveis CSS, tema global
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── desktop/
│   └── tauri/              ← Tauri v2 (Rust)
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       ├── build.rs
│       └── src/
│           ├── main.rs
│           └── lib.rs
├── docs/
├── scripts/
├── README.md
└── .gitignore
```

## Princípios da Migração

1. **Coexistência** — sistema legado continua em produção até migração completa
2. **Por camadas** — backend primeiro, depois frontend, depois desktop
3. **Módulos reutilizados** — código Python existente é adaptado como serviços
4. **API primeiro** — toda comunicação via REST; nada de WebSocket/Eel
5. **Enterprise-ready** — arquitetura preparada para crescimento

## Status da Migração

| Componente | Status | Observação |
|-----------|--------|-----------|
| Estrutura de pastas | ✅ Completo | 56 arquivos criados |
| Backend FastAPI base | ✅ Completo | Config, logging, database, healthcheck |
| Frontend React base | ✅ Completo | Rotas, layout, tema, API service |
| Desktop Tauri | ✅ Completo | Config inicial, hello world |
| Módulo BPA | ⬜ Pendente | |
| Módulo Recepção (backend) | ✅ Completo | API REST com CRUD + hospital.db |
| Módulo Recepção (frontend) | ✅ Completo | Ficha A4 com busca, cadastro, impressão |
| Impressão A4 (Boletim Atendimento) | ✅ Completo | Réplica exata do legado + tabela SSVV + áreas caligrafia |
| Módulo Relatórios | ⬜ Pendente | |
| Automações legado | ⬜ Pendente | Adaptar como serviços |
| Integração Firebird | ⬜ Pendente | |
| Testes | ⬜ Pendente | |

## Sessões

### Sessão 1 — 2026-05-16 — Fundação

Criação da estrutura completa do projeto `hmcpf-system/`:
- Backend FastAPI com config, logging, database, healthcheck
- Frontend React + Vite com sidebar, rotas, tema dark/light
- Desktop Tauri v2 com configuração inicial
- README profissional com comandos de instalação

**Arquivos:** 56 criados
**Linhas de código:** ~800 (base inicial)

### Sessão 2 — 2026-05-16 — Comentários didáticos

Todos os arquivos do `hmcpf-system/` foram revisados e receberam comentários educativos em português explicando:
- **Propósito** de cada arquivo e diretório
- **Conceitos** (O que é FastAPI? Context React? ORM? Tauri?)
- **Padrões** de arquitetura (layered, service layer, template method)
- **Fluxo** de dados (requisição → endpoint → service → banco)
- **Por que** cada decisão foi tomada (Axios em vez de fetch, Vite em vez de Webpack)
- **Como usar** cada função/classe com exemplos práticos

Objetivo: o código serve como material de estudo para entender a arquitetura enterprise.

### Sessão 3 — 2026-05-16 — Backend da Recepção (API + hospital.db)

**Objetivo:** Expor dados do `hospital.db` legado via REST API (FastAPI) para substituir o Eel.

**O que foi criado:**

| Arquivo | Função |
|---------|--------|
| `backend/app/modules/recepcao/schemas.py` | Modelos Pydantic (PacienteCreate, PacienteResponse, AtendimentoResponse, PaginatedResponse) |
| `backend/app/modules/recepcao/service.py` | Lógica de negócio (CRUD pacientes + atendimentos, conexão direta com hospital.db via sqlite3) |
| `backend/app/api/v1/recepcao.py` | Endpoints REST (listar, buscar, criar, atualizar, deletar pacientes + listar atendimentos + estatísticas) |

**Endpoints criados:**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/recepcao/pacientes` | Listar pacientes (filtro por nome/CPF, paginação) |
| GET | `/api/v1/recepcao/pacientes/{cpf}` | Buscar por CPF |
| POST | `/api/v1/recepcao/pacientes` | Criar paciente |
| PUT | `/api/v1/recepcao/pacientes/{cpf}` | Atualizar paciente |
| DELETE | `/api/v1/recepcao/pacientes/{cpf}` | Deletar paciente |
| GET | `/api/v1/recepcao/atendimentos` | Listar atendimentos (com JOIN pacientes) |
| GET | `/api/v1/recepcao/estatisticas` | Totais (29.940 pacientes, 10.144 atendimentos) |

**Arquivos modificados:**

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/core/config.py` | + `LEGACY_DB_PATH`, + `PROJECT_ROOT` (path hospital.db) |
| `backend/app/main.py` | + import + include_router do recepcao |
| `backend/.env` | + `LEGACY_DB_PATH=` |

**Testes:** Todos os endpoints funcionando — API servindo dados reais do hospital.db.

### Sessão 4 — 2026-05-16 — Frontend da Recepção (Ficha A4)

**Objetivo:** Criar página de cadastro de pacientes com busca, formulário A4 e impressão.

**O que foi criado:**

| Arquivo | Função |
|---------|--------|
| `frontend/src/pages/Recepcao.jsx` | Página completa: busca, resultados, formulário A4, salvar, imprimir |
| `frontend/src/pages/Recepcao.css` | Estilo ficha A4 com @media print (oculta sidebar/menus na impressão) |

**Funcionalidades:**
- Busca por nome ou CPF (digita + Enter ou botão Buscar)
- Lista de resultados clicáveis → preenche formulário
- Formulário com campos organizados: Identificação, Filiação, Contato
- Salvar (POST se novo, PUT se existente)
- Imprimir (Ctrl+P ou botão) — formatação A4 automática
- Botão Novo/Limpar para cadastro em branco

**Arquivos modificados:**

| Arquivo | Alteração |
|---------|-----------|
| `frontend/src/routes/index.jsx` | + rota `/recepcao` → `<Recepcao />` |

**Build:** Frontend compila sem erros (262 KB JS, 8 KB CSS).

### Sessão 5 — 2026-05-16 — Impressão A4 idêntica ao legado

**Objetivo:** Replicar exatamente o layout de impressão do sistema legado (`web_recepcao/index.html`) — o "Boletim de Atendimento" padrão do hospital.

**O que foi criado:**

| Arquivo | Função |
|---------|--------|
| `frontend/src/components/FichaA4Print.jsx` | Componente oculto na tela, visível apenas na impressão. Renderiza o HTML idêntico ao legado com cabeçalho, dados do paciente, tabela SSVV colorida, comorbidades, áreas de escrita manual |
| `frontend/src/components/FichaA4Print.css` | CSS de impressão com `@page { size: A4; margin: 0; }`, `.page { width: 210mm; }`, tabela de risco com cores, áreas de linha para caligrafia |
| `frontend/public/logo.png` | Logomarca do hospital (copiada de `web_recepcao/logo.png`) |

**Diferenças entre tela e impressão:**

| | Tela (React) | Impressão (A4) |
|--|-------------|----------------|
| Layout | Formulário editável moderno | Boletim de Atendimento exato do legado |
| Busca | ✅ Campo de busca + resultados | ❌ Oculto |
| Parte médica | ❌ Não exibida | ✅ SSVV, comorbidades, anamnese em branco |
| Cabeçalho | Logo + "HMPCF" na sidebar | Logo + "HMPCF" + texto institucional completo |
| Cor | Variáveis CSS tema dark/light | Preto e branco + cores SSVV preservadas |

**Arquivos modificados:**

| Arquivo | Alteração |
|---------|-----------|
| `frontend/src/pages/Recepcao.jsx` | + import + `<FichaA4Print paciente={form} />` |
| `frontend/src/components/Sidebar.jsx` | + logo do hospital no cabeçalho da sidebar |

**Resultado:** A impressão (Ctrl+P) sai exatamente igual ao padrão do hospital — parte administrativa preenchida, parte médica em branco para preenchimento manual.
