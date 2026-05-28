# Migração SQLite → PostgreSQL — HMPCF

Script ETL profissional para transferir dados do banco legado (`hospital.db`)
para o PostgreSQL do novo sistema HMPCF.

---

## Pré-requisitos

- Python 3.12+
- PostgreSQL 16 rodando (local ou Docker)
- `hospital.db` disponível (um nível acima de `hmcpf-system/`)
- Tabela `pacientes` já criada no PostgreSQL (via Alembic ou `recreate_pacientes.py`)

---

## Instalação das dependências

```bash
cd hmcpf-system
pip install -r requirements.txt
```

---

## Configuração

```bash
# Copie o template e edite com suas credenciais reais
cp .env.example .env
```

Edite o arquivo `.env`:

```env
SQLITE_PATH=../hospital.db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hmpcf
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha_aqui
LOG_FILE=migration.log
BATCH_SIZE=500
```

---

## Execução

### 1. Simulação (recomendado antes da migração real)

```bash
python migrate_to_postgres.py --dry-run
```

Processa todo o ETL (extrai, transforma, valida) **sem gravar nada** no PostgreSQL.
Ideal para verificar avisos de dados, contagens e potenciais erros.

### 2. Migração completa

```bash
python migrate_to_postgres.py
```

Insere apenas os registros novos (não duplica por CPF ou CNS).
Idempotente: pode ser executado múltiplas vezes com segurança.

### 3. Re-migração limpa (apaga tudo antes)

```bash
python migrate_to_postgres.py --truncate
```

> **ATENÇÃO:** Remove **todos** os registros de `pacientes` e
> `recepcao_atendimentos` antes de migrar.
> Use somente quando houver backup confirmado.

---

## Garantias de segurança

| Garantia | Como é implementado |
|----------|---------------------|
| SQLite somente leitura | URI `file:///...?mode=ro` — qualquer escrita lança `OperationalError` |
| Credenciais via `.env` | Nunca hardcoded no código |
| Deduplicação | CPF e CNS verificados contra o PostgreSQL antes de cada INSERT |
| Rollback automático | Falha de lote => rollback + fallback individual |
| Sem interrupção | Datas/campos inválidos viram `NULL` com aviso no log |

---

## Mapeamento de colunas

| SQLite (`hospital.db`) | PostgreSQL (`pacientes`) | Transformação |
|------------------------|--------------------------|---------------|
| `sus` | `cns` | Remove não-dígitos, máx 15 chars |
| `cpf` | `num_cpf` | Remove não-dígitos, máx 11 chars |
| `nome` | `nome` | Trunca a 100 chars |
| `dn` | `dtnasc` | Converte para YYYYMMDD |
| `sexo` | `sexo` | M/F → M/F; outro → I |
| `raca` | `raca` | Texto/código → 01–05 (CADCNS) |
| `mae` | `maepcn` | Trunca a 100 chars |
| `endereco` | `logpcn` | Default: `PRINCIPAL` |
| `numero` | `numpcn` | Default: `S/N` |
| `bairro` | `bairro_pcnte` | Default: `CENTRO` |
| `naturalidade` | `nmres` | Trunca a 100 chars |
| `naturalidade` | `naturalidade` | Idem (campo duplicado propositalmente) |
| `tel` | `ddtel_pcnte` + `tel_pcnte` | Separa DDD do número |
| `nomeSocial` | `nome_social` | Trunca a 100 chars |
| `idade` | `idade` | Trunca a 50 chars |
| `civil` | `civil` | Trunca a 50 chars |
| `ocupacao` | `ocupacao` | Trunca a 100 chars |
| `responsavel` | `responsavel` | Trunca a 100 chars |
| `cidade` | `cidade` | Trunca a 100 chars |
| `estado` | `estado` | 2 letras maiúsculas |
| *(sem equivalente)* | `ibge` | Default: `240360` (Extremoz/RN) |
| *(sem equivalente)* | `ceppcn` | Default: `59575000` |
| *(sem equivalente)* | `co_lograd` | Default: `081` (RUA) |
| *(sem equivalente)* | `nacionalidade` | Default: `010` (Brasileiro) |

---

## Arquivos gerados

| Arquivo | Descrição |
|---------|-----------|
| `migration.log` | Log completo (DEBUG+) com todos os avisos e erros |

---

## Verificação pós-migração

```sql
-- Contagem total de pacientes migrados
SELECT COUNT(*) FROM pacientes;

-- Pacientes sem CPF nem CNS (registros não identificáveis)
SELECT COUNT(*) FROM pacientes
WHERE num_cpf IS NULL AND cns IS NULL;

-- Distribuição por raça
SELECT raca, COUNT(*) FROM pacientes GROUP BY raca ORDER BY raca;

-- Últimos migrados
SELECT nome, num_cpf, cns, dtnasc, migrated_at
FROM pacientes
ORDER BY migrated_at DESC
LIMIT 10;
```
