# Histórico de Desenvolvimento — HMPCF

Registro das decisões técnicas e marcos do projeto. Detalhes de implementação
estão no código e nos commits do git.

---

## 2026-05-24 — Migração inicial e módulos core

**Contexto:** Primeiro dia do novo sistema. Banco de dados zerado, código do zero.

### O que foi feito
- Migração SQLite → PostgreSQL: **28.672 pacientes** via `migrate_v2.py`
- Todas as colunas renomeadas para **snake_case** (PostgreSQL trata sem aspas como lowercase — manter UPPERCASE exigiria aspas em todo lugar)
- Módulos implementados: Pacientes, Recepção, Histórico, Terminal
- Frontend React integrado ao backend FastAPI

### Decisões de schema

| Tabela | Observação |
|--------|-----------|
| `pacientes` | Colunas snake_case, campo `registro` adicionado |
| `recepcao_atendimentos` | FK → pacientes, campo `registro` (número no turno) |

### Migrations aplicadas
```
0001            → Initial pacientes (stampado — banco já existia via ETL)
f61017de2d75    → add_recepcao_atendimentos
a3f8c2e1b5d9    → add_nacionalidade_to_pacientes
b1c2d3e4f5a6    → add_registro_to_recepcao_atendimentos
```

### Bug crítico corrigido
`useEffect` em `Recepcao.jsx` referenciava `autoBusca` antes da declaração do `useCallback` (TDZ — Temporal Dead Zone). Correção: mover o `useEffect` para depois do `useCallback`.

---

## 2026-05-25 manhã — Testes e busca agrupada

### O que foi feito
- **Limpeza do legado:** removidos `database_pg.py`, `database.py`, `routes/`, `main.py` legado do backend
- **21 testes automatizados** implementados (pytest + PostgreSQL do Docker)
- **Novo endpoint:** `GET /api/v1/recepcao/pacientes/agrupado?q=...`

### Endpoint de busca agrupada
Problema: `GET /recepcao/` retornava uma linha por atendimento — pacientes com múltiplas visitas poluíam a listagem.

Solução: GROUP BY + COUNT + MAX via JOIN:
```sql
SELECT paciente_id, nome, num_cpf, cns, dtnasc,
       COUNT(id) AS total_entradas,
       MAX(data_atendimento) AS ultima_data
FROM recepcao_atendimentos JOIN pacientes ...
GROUP BY paciente_id, nome, num_cpf, cns, dtnasc
ORDER BY ultima_data DESC
```

### Cobertura de testes

| Suite | Testes | O que cobre |
|-------|--------|-------------|
| `test_paciente_repository` | 8 | get_by_cpf, get_by_cns, search, count |
| `test_recepcao_repository` | 7 | add, list, grouped, count |
| `test_recepcao_service` | 6 | listar_agrupado, criar_atendimento |

---

## 2026-05-25 tarde — Script ETL profissional e primeira subida real

### O que foi feito
- Reescrita completa do script de migração (`migrate_to_postgres.py`)
- Primeira execução real: sistema novo rodando com dados do hospital
- Correção dos campos BPA (`ibge`, `ceppcn`, `co_lograd`, `naturalidade`)

### Resultado da migração definitiva

| Tabela | SQLite | PostgreSQL | Descartados |
|--------|--------|------------|-------------|
| `pacientes` | 30.496 | 29.242 | 1.254 (duplicatas/sem identificador) |
| `recepcao_atendimentos` | 11.758 | 11.687 | 71 (duplicatas/sem paciente) |

### Defaults BPA corrigidos

| Campo | Problema | Solução |
|-------|----------|---------|
| `ibge` | `"240390"` (errado) | `"240360"` (Extremoz/RN) |
| `ceppcn` | NULL (server_default ignorado) | Default Python `"59575000"` no schema |
| `co_lograd` | NULL | Default Python `"081"` |
| `nacionalidade` | NULL | Default Python `"010"` (Brasil) |
| `naturalidade` | Apontava para campo errado no frontend | Corrigido `name="naturalidade"` no BoletimA4 |

---

## 2026-05-26 — Validações, limpeza de dados e prontidão

### O que foi feito
- Remoção da coluna `nmres` (naturalidade mal mapeada do legado)
- Limpeza de valores padrão falsos do legado no banco
- Validações obrigatórias no backend e frontend
- Correções de UX (registro persistente, botão Família)

### Limpeza de dados legados

| Campo | Valor falso removido | Linhas afetadas |
|-------|---------------------|-----------------|
| `logpcn` | `"PRINCIPAL"` | 14.941 |
| `numpcn` | `"S/N"` | 15.012 |
| `bairro_pcnte` | `"CENTRO"` | 16.621 |

### Validações implementadas (`schemas/paciente.py`)

| Campo | Regra |
|-------|-------|
| `nome` | Obrigatório, mín. 3 caracteres |
| `num_cpf` | Validação matemática (dígitos verificadores) |
| `cns` | Validação matemática (mod 11) |
| `sexo` | Apenas `M` ou `F` |
| `dtnasc` | Obrigatória, YYYYMMDD, não futura, não > 130 anos |
| `num_cpf` ou `cns` | Pelo menos um presente e válido |

Adicionada constraint `UNIQUE (num_cpf)` no banco.

### Estado do banco ao final

```
pacientes:
  - nmres: REMOVIDA
  - logpcn, numpcn, bairro_pcnte: nullable, sem default falso
  - num_cpf: UNIQUE CONSTRAINT (uq_pac_cpf)
  - num_cpf e cns: UNIQUE
```

### Pendências de produção (ainda abertas)

| # | Item |
|---|------|
| 🔴 | Frontend: `npm run build` + servidor estático (não depender do Vite dev) |
| 🔴 | Backend como serviço Windows (não depender de terminal aberto) |
| 🔴 | Backup diário automatizado do PostgreSQL |

---

## 2026-05-28 — Reestruturação, limpeza e preparação para produção

### Reestruturação do repositório
- Legado movido para `legado/` (intocado, em produção); novo sistema promovido para a raiz
- Correção do nome: `hmcpf-system` → `hmpcf-system` em todos os docs
- `INICIAR.bat` atualizado com caminhos corretos
- Novo `README.md` com tabela de status da migração

### Limpeza do repositório
- Docs: 7 arquivos → 3 (`HISTORICO.md`, `ARQUITETURA.md`, `MIGRACAO.md`) — 4 diários de sessão consolidados
- `frontend/verify_*.png` e `verify_*.mjs` removidos (artefatos de verificação manual)
- `legacy_reference/` removido (versões descartadas do ETL)
- `.env.example` duplicado da raiz removido
- `.opencode/` removido e adicionado ao `.gitignore`

### Fix de duplo registro acidental — `Recepcao.jsx`
Estado `registrado` desabilita o botão "Registrar Atendimento" após sucesso até o usuário clicar "Limpar". Impede criar dois atendimentos idênticos no mesmo clique.

### Preparação para produção
- `backend/app/main.py`: `GZipMiddleware`, CORS dinâmico via `.env`, `StaticFiles` serve `frontend/dist/`, SPA fallback, `/docs` oculto em `ENVIRONMENT=production`
- `INICIAR.bat`: usa `.venv\Scripts\python.exe`, `--host 0.0.0.0 --port 8001`, sem `--reload`, sem `npm run dev`, inicia Docker
- Frontend buildado: 3 chunks (~229 KB total, ~75 KB gzip)
- Scripts novos: `backup_postgres.bat` (pg_dump nativo), `instalar_servico.bat` (NSSM), `agendar_backup.ps1` (Task Scheduler)

### Decisão: PostgreSQL nativo em produção (sem Docker)
PC de recepção Windows 24h não se beneficia do Docker — adiciona ~500 MB RAM, ponto de falha extra (Docker Desktop) e complexidade desnecessária. PostgreSQL instala como serviço Windows nativo com auto-start.

### Guia de deploy — `docs/DEPLOY_HOSPITAL.md`
11 seções cobrindo do zero ao checklist final: instalação, banco, migração, build, serviço Windows, backup, rede LAN, 30 itens de checklist.

### Próximo passo
Deploy em PC de **teste** primeiro para validar migração e fluxo completo antes do PC real da recepção.

---

## 2026-05-28/29 — Migração definitiva, validação e preparação do deploy Windows

### Ambiente de teste (CachyOS)
- PostgreSQL do HMPCF subido via Docker na porta **5433** (porta 5432 ocupada por outro projeto)
- `backend/.env` criado com credenciais e porta correta
- Tabelas criadas via `SQLAlchemy create_all()` (projeto não usa Alembic)
- Backend iniciado com `uvicorn --reload`, frontend com `vite --host 0.0.0.0`
- **Bug corrigido:** `api.js` chamava `POST /pacientes` sem trailing slash → 405 Method Not Allowed. Corrigido para `/pacientes/`

### Melhorias no script de migração (`migrate_to_postgres.py`)

**Validação matemática adicionada:**

| Documento | Regra anterior | Regra nova |
|-----------|---------------|------------|
| CPF | Remove não-dígitos, aceita 8–11 dígitos | Exige exatamente 11 dígitos + algoritmo mod 11 |
| CNS/SUS | Remove não-dígitos, limita a 15 chars | Exige 15 dígitos + soma ponderada DATASUS divisível por 11 |

**Política de pacientes sem documento:**
- Antes: tentava dedup fuzzy por nome≥90% + dtnasc; se não duplicado, entrava sem identificador
- Agora: **rejeitado na origem** — sem CPF válido E sem CNS válido = descartado com contador próprio

**Atendimentos migrados** (novo pipeline adicionado ao script):
- Resolve `paciente_id` pelo CPF ou CNS do atendimento (lookup no PostgreSQL)
- Combina `data_atendimento` + `hora_atendimento` → `TIMESTAMPTZ`
- Dedup por `(paciente_id, data_atendimento)` exato
- Atendimentos cujo paciente foi barrado pela validação são descartados com aviso

**Bug de dry-run corrigido:** `if pg_conn:` trocado por `if not dry_run:` em todos os pontos de inserção — o dry-run conecta ao PG para leitura (mapa de pacientes, dedup) mas não escreve nada.

### Resultado da migração definitiva

| Tabela | SQLite | Migrados | Descartados |
|--------|--------|----------|-------------|
| `pacientes` | 30.877 | **29.464** | 1.259 dup + 587 CPF inválido + 274 CNS inválido + 154 sem documento |
| `recepcao_atendimentos` | 12.926 | **12.831** | 67 dup + 28 sem paciente |

### Limpeza de dados no banco
- **154 pacientes** sem CPF nem CNS deletados do PostgreSQL (nenhum tinha atendimento vinculado)
- Atendimento de teste criado durante verificação removido

### Tela de Histórico — simplificação das colunas
Removido da tabela de atendimentos expandida: **Classificação de Risco**, **Procedência**, **Observações** (campos que só são preenchidos manualmente no sistema novo).

Adicionado: **CPF**, **Cartão SUS**, **Dt. Nascimento** — vindos do `paciente` já disponível no escopo.

### Estado final do banco (pronto para produção)

```
pacientes:             29.464  (todos com CPF ou CNS válido)
recepcao_atendimentos: 12.831
sem_documento:             0
```

### Próximo passo
Deploy no PC da recepção (Windows) seguindo `docs/DEPLOY_HOSPITAL.md`.
