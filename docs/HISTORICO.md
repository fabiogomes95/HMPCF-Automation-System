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

## 2026-05-28 — Reestruturação do repositório

- Todo o sistema legado movido para `legado/`
- Conteúdo de `hmcpf-system/` promovido para a raiz
- Correção do nome: `hmcpf-system` → `hmpcf-system`
- `INICIAR.bat` atualizado
- Novo `README.md` refletindo o estado atual da migração
