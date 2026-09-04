# Histórico de Desenvolvimento — HMPCF

Registro das decisões técnicas e marcos do projeto. Detalhes de implementação
estão no código e nos commits do git.

---

## 2026-09-04 — Reorganização de pastas (auditoria + arquivamento)

### Estrutura de pastas

- `bpa/bpa_gerador_bckp.py` (backup manual esquecido, sem referência no
  código) movido para `bpa/legado/`.
- `scripts/importacao/importar_planilha_junho2026.py` (one-off, já
  executado) arquivado em `scripts/importacao/legado/` — caminhos
  relativos (`.env`, planilha csv) ajustados pra nova profundidade.
- `scripts/migrations/archive/` renomeado para `scripts/migrations/legado/`
  — padroniza o nome com as demais pastas de arquivamento do repo.
- `docs/AUDITORIA_BPA_2026-06.md`, `docs/PENDENCIAS_2026-07-03.md` e
  `docs/MIGRACAO.md` movidos para `docs/historico/` — separa registros de
  um momento específico da documentação viva (`ARQUITETURA.md`,
  `DEPLOY_HOSPITAL.md`, `INSTALACAO_*.md`).
- `docker-compose.yml` e o `.env.example` da raiz (específicos do compose)
  arquivados em `legado/docker-compose/`, com `NOTA.md` explicando a
  descontinuação — desde então o PostgreSQL roda como instalação nativa
  também em desenvolvimento, não só em produção.
- `bpa/auditoria_mensal/` avaliado e **mantido no lugar** (uso frequente,
  não é código morto apesar de ter nascido de um incidente pontual).
- Os três launchers redundantes do backend (`INICIAR.bat`,
  `scripts/windows/ABRIR_HMPCF.bat`, `iniciar_sistema.vbs`) **não foram
  tocados** — seguem com o mesmo problema já registrado na entrada de
  02/07/2026 (não dá pra saber pelo repo qual está no Agendador de
  Tarefas); antes de consolidar, teste numa máquina de teste.

## 2026-07-02 — Hardening de segurança, incidente de produção e reorganização de pastas

### Segurança
- Senha real do PostgreSQL (estava commitada em texto puro em 3 arquivos, repo
  público) rotacionada e removida do código — scripts de deploy/backup agora
  pedem a senha ou leem de `backend/.env`, nunca hardcoded.
- Rede da `desktop-9c4s1co` corrigida de "Public" para "Private"; firewall da
  porta 8001 restrito a Domain/Private.
- `bpa/app.py`: parâmetro de mês validado (regex `AAAAMM`) antes de montar a
  query SQL.
- `docker-compose.yml`: senhas obrigatórias (sem default fraco), portas do
  Postgres/pgAdmin/backend bindadas em `127.0.0.1`.
- CPF/CNS mascarados nos logs de `scripts/importacao/PREPARAR_BPA_MENSAL.py`.
- Backup do Postgres agora criptografado (AES-256) via
  `scripts/windows/encrypt_backup.ps1` — senha em arquivo local não
  versionado (`scripts/windows/.backup_passphrase`).

### Incidente e causa raiz
Rotação da senha do Postgres expôs um bug: a senha continha `@`, que quebrava
o parsing da connection string (`postgresql+asyncpg://user:senha@host...`) —
`host` era interpretado errado, derrubando toda query ao banco (busca de
paciente com erro 500) por ~15 min até o diagnóstico. Corrigido
permanentemente em `backend/app/core/config.py` (senha agora passa por
`urllib.parse.quote_plus` antes de montar a URL — funciona com qualquer
senha dali pra frente).

Durante o diagnóstico, foi descoberto que **dois mecanismos de auto-restart
do backend coexistiam**: a Tarefa Agendada `HMPCF-Backend`/`HMPCF-Watchdog`
(de `registrar_servico.ps1`) e o Serviço Windows via NSSM
`HMPCF-Backend-Svc` (de `instalar_servico.bat`) — os dois competiam pela
porta 8001 a cada restart, causando erros `10048` (porta em uso). As duas
Tarefas Agendadas foram **desativadas**; o Serviço NSSM `HMPCF-Backend-Svc`
é agora o único responsável por manter o backend no ar.

### Estrutura de pastas
- `dashboard/bpa_gerador.py` movido para `bpa/bpa_gerador.py` (fonte única do
  BPA-I não morava mais no Streamlit desde a remoção da página `4_BPA.py`,
  só o arquivo tinha ficado pra trás). `bpa/requirements.txt` criado;
  `passlib` (não usado por ninguém) removido de `dashboard/requirements.txt`.
- `scripts/migrations/migrate_to_postgres.py` arquivado em
  `scripts/migrations/archive/` (migração SQLite→Postgres já concluída).
- `docs/ARQUITETURA.md` e `README.md` corrigidos: pasta `docker/` não existe
  (nunca existiu de fato), produção não usa Docker.
- `INICIAR.bat`, `scripts/windows/ABRIR_HMPCF.bat` e `iniciar_sistema.vbs`
  (três launchers com lógica parecida) documentados com comentário cruzado
  — não consolidados/removidos porque não foi possível confirmar
  remotamente qual está registrado no Agendador de Tarefas (comando
  `Get-ScheduledTask` trava por limitação de duplo-hop do WinRM nesta
  topologia).

---

## 2026-06-17 — Painel Gerencial (Streamlit): construção, correção de dados reais e importação mensal

### Contexto

Pedido: um painel separado da recepção, para coordenadores do hospital e TI
acompanharem pacientes em tempo real (hoje/semana/mês/desde o início), sem
risco nenhum de afetar o backend/frontend da recepção (que está em produção
e não deveria ser tocado).

### Decisão de arquitetura

Aplicação **Streamlit totalmente independente** em `dashboard/`:
- Ambiente virtual próprio (`dashboard/.venv`), instalado e executado
  **diretamente no Desktop-9c4s1co** (a máquina real da recepção), não no
  backend.
- Porta própria (**8502**), separada da porta 8001 do backend.
- Conexão somente leitura ao mesmo PostgreSQL, reaproveitando as credenciais
  de `backend/.env` (sem duplicar segredo, sem nenhuma alteração no backend).
- Tarefa Agendada própria (`HMPCF-Dashboard`), com `BootTrigger` e reinício
  automático — mesmo padrão da `HMPCF-Backend`, mas totalmente desacoplada.
- Regra de firewall própria (porta 8502) — a do backend (8001) não foi tocada.

Alternativa descartada: rodar o Streamlit em outra máquina (PC do TI) e
expor o PostgreSQL na rede. Rejeitada para não aumentar a superfície de
exposição do banco de produção; o processo continua só no Desktop-9c4s1co e
qualquer máquina da rede acessa via navegador.

### Armadilha: dois ambientes parecidos

Boa parte da sessão foi gasta tentando rodar e testar o dashboard — sem
perceber, inicialmente, que o ambiente de execução (Bash local) era o PC
pessoal do desenvolvedor, não o Desktop-9c4s1co real. O `.venv` e os testes
iniciais rodaram contra uma **cópia local do backup noturno** do Postgres
(dados reais, mas até 1 dia desatualizados), não contra o banco em produção.
Identificado pela disparidade de hostname/IP/usuário (`DESKTOP-MPE1OD9` /
`192.168.1.100` / `pedro` vs. o real `DESKTOP-9C4S1CO` / `192.168.1.14` /
`Recepção 02`). Resolvido recriando a `.venv` e reinstalando tudo via WinRM,
executando de fato no Desktop-9c4s1co.

### Páginas implementadas

| Página | Função |
|---|---|
| `app.py` (principal) | KPIs (hoje/semana/mês/total), volume diário, sexo, faixa etária, top 10 bairros |
| `pages/1_Historico_Diario.py` | Lista completa de atendimentos de um dia (hoje/ontem/escolher data), com CPF, CNS, nascimento, idade, sexo, endereço, telefone |
| `pages/2_Importar_Planilha_Mensal.py` | Upload do `.tsv` de plantão → compara com o banco → importa só o que falta, com prévia e confirmação manual |
| `pages/3_Buscar_Paciente.py` | Busca por nome/CPF/CNS → todas as entradas (data e horário) daquele paciente |

Código compartilhado em `db.py` (conexão, formatação de CPF/telefone/endereço,
cálculo de idade, correção de fuso, deduplicação) e `importador.py` (parser
do `.tsv`, comparação e importação).

### Bugs reais encontrados e corrigidos

**1. Fuso horário (+3h em todos os horários exibidos).**
`pandas.read_sql` convertia os `timestamptz` para UTC, descartando o
offset `-03:00`. O Postgres em si estava com a hora certa (`now()` batia
com o relógio do Windows) — o bug era só na exibição. Corrigido com
`corrigir_fuso()` (reaplica `America/Sao_Paulo` após a leitura).

**2. `TypeError` em campos nulos.** CPF, telefone e endereço nulos chegam
como `NaN` (float) via pandas, não como `None`/string vazia — quebrava
`len(cpf)`. Corrigido com normalização (`_texto()`) em todas as funções de
formatação.

**3. Parser do `.tsv` confundindo data de nascimento com cabeçalho de dia.**
Uma linha tinha o CPF digitado por engano no campo de número de registro;
como esse campo não era um número puro, o parser caía num fallback e
interpretava a data de nascimento do paciente (`22/03/1989`) como se fosse
o cabeçalho do dia, corrompendo a data de todos os atendimentos seguintes.
Corrigido: só vira cabeçalho de dia uma linha que bate exatamente com o
padrão de data isolada ou contém "PLANT" (plantão). Linhas não reconhecidas
vão para uma lista de "ignoradas", exibida na tela para revisão manual.

**4. Erro de digitação no ano do cabeçalho.** Um cabeçalho de plantão tinha
"13/06/**2016**" em vez de 2026 (erro humano da recepção). Corrigido com
correção automática: o mês/ano do **primeiro** cabeçalho válido do arquivo
é usado como referência; qualquer cabeçalho que destoe tem o ano/mês
substituído (mantendo o dia).

**5. Regra do plantão noturno.** Confirmado contra dados reais: um
atendimento da madrugada (ex: 00:04) sob o cabeçalho "PLANTÃO NOTURNO
01/06" é gravado no sistema com a data do dia **seguinte** (02/06) — o
plantão noturno cruza a meia-noite e a recepção digita pela data/hora real,
não pela data de início do plantão. O parser agora aplica essa mesma regra
(virada de dia para horários antes das 07h sob plantão noturno), o que
**reduziu de 554 para 254** o número de atendimentos realmente faltantes no
sistema (o número de 554 estava inflado por essa divergência de data).

**6. Lançamentos duplicados por erro de digitação da recepção.** Mesmo
paciente, mesmo dia, mesmo número de registro ou horário a poucos minutos de
distância (ex: 10:09 e 10:14) — não são duas visitas reais, são reentrada
por engano. `remover_quase_duplicados()` (limite padrão: 30 minutos) mantém
só o lançamento mais recente do par, em todas as páginas do painel
(KPIs, gráficos, histórico diário, busca de paciente). Os duplicados nunca
são apagados do banco — só ficam ocultos na visualização, com um aviso
expansível mostrando o que foi escondido.

### Importação de dados reais

Durante os testes, dois atendimentos manuais que nunca tinham sido digitados
foram identificados e importados (Izadora Liz Ferreira Bezerra, registro 59;
Rafaela Silva do Nascimento, registro 60 — ambos de madrugada, plantão
noturno). A varredura completa de junho/2026 identificou **254 atendimentos**
registrados no papel mas ausentes do sistema — ficou disponível para
importação assistida (com prévia e confirmação manual) na página
"Importar Planilha Mensal", reutilizável em qualquer mês seguinte.

### Decisões de segurança

- O dashboard nunca escreve no banco fora da tela de importação, e mesmo lá
  exige confirmação explícita (checkbox + botão) antes de qualquer `INSERT`.
- Toda alteração de infraestrutura (firewall, tarefa agendada, exclusão de
  pasta) foi feita com confirmação explícita do usuário quando o sistema de
  segurança do agente sinalizou risco — nenhuma tentativa de contornar essas
  proteções (ex: elevação de privilégio via tarefa agendada) foi realizada.
- `dashboard/.venv` está no `.gitignore` (já coberto pelo padrão `.venv/`).

---

## 2026-05-29 — Migração definitiva, auditoria e boletim A4

### Script de migração (`scripts/migrate_to_postgres.py`)

Script único que substitui `recreate_pacientes.py` (deletado). Roda uma vez
só no PC da recepção e faz tudo:

1. Cria as tabelas `pacientes` e `recepcao_atendimentos` com DDL exato do
   modelo SQLAlchemy (inclui enum `classificacao_risco_enum`, colunas
   `created_at`, `updated_at`, `observacoes`, `historia_clinica`, etc.)
2. Migra pacientes do SQLite legado (colunas antigas: `cpf`, `sus`, `dn`,
   `mae`, `endereco`…) para o PostgreSQL (colunas BPA: `num_cpf`, `cns`,
   `dtnasc`, `maepcn`, `logpcn`…)
3. Migra atendimentos vinculando pelo CPF/CNS do paciente
4. Validação matemática CPF (mod 11) e CNS (DATASUS checksum)
5. Deduplicação por CPF/CNS exato; idempotente (pode rodar N vezes)

**Mapeamento de colunas (SQLite → PostgreSQL):**

| SQLite (legado) | PostgreSQL | Tratamento |
|---|---|---|
| `cpf` | `num_cpf` | Validação mod 11 |
| `sus` | `cns` | Validação DATASUS |
| `nome` | `nome` | UPPERCASE |
| `dn` | `dtnasc` | Formato YYYYMMDD |
| `mae` | `maepcn` | — |
| `endereco` | `logpcn` | — |
| `numero` | `numpcn` | — |
| `bairro` | `bairro_pcnte` | — |
| `tel` | `ddtel_pcnte` + `tel_pcnte` | Separa DDD do número |
| `naturalidade` | `naturalidade` | Campo livre (cidade de nascimento) |
| — | `nacionalidade` | Fixo: `"010"` (código BPA brasileiro) |
| — | `ibge` | Fixo: `"240360"` |
| — | `ceppcn` | Fixo: `"59575000"` |
| — | `co_lograd` | Fixo: `"081"` |

**Bug corrigido — timezone nos atendimentos:**  
`_carregar_chaves_atd` retornava `datetime` com timezone (TIMESTAMPTZ do PG)
mas o parser SQLite retorna naive datetime. Comparação sempre falhava → todos
os atendimentos eram re-inseridos a cada execução (duplicatas). Fix:
`.replace(tzinfo=None)` ao carregar do PG.

**Dedup de atendimentos (`_dedup_atendimentos`):**  
Função nova que roda antes de inserir. Remove duplicatas existentes no PG
(mantém o menor `id` de cada grupo `paciente_id + data_atendimento`).
Garante idempotência mesmo após execuções parciais anteriores.

**`SQLITE_TABLE` env var:**  
Permite escolher a tabela de origem (`pacientes` ou `pacientes_backup`).
Padrão: `pacientes`. Útil para migrar do backup quando a tabela principal
já foi renomeada para formato BPA.

---

### Auditoria pré-produção (10 correções)

**Frontend (`Recepcao.jsx`):**
- Bug data de nascimento: mensagem de erro persistia mesmo após digitar data
  válida. Fix: `handleDtnascChange` chama `setErroDtnasc("")` quando
  `calcularIdade(fmt)` retorna objeto válido.
- Modo edição: `setRegistrado(false)` no `useEffect` de edição, evitando
  botão "Salvar" travado.

**Backend:**
- `recepcao_service.py`: `remover()` usava `repo.get()` (base, sem carregar
  relação); corrigido para `get_by_id()`.
- `schemas/paciente.py`: `PacienteUpdate.nacionalidade` era `Optional=None`,
  podendo gerar erro 500 (coluna NOT NULL). Fix: default `"010"`.
- `models/recepcao_atendimento.py`: `BigInteger` → `Integer` para `id` e
  `paciente_id`, consistente com `pacientes.id`.
- DDL `pacientes`: VARCHAR expandidos para 100 chars, colunas nullable
  corrigidas, `naturalidade` adicionada, `num_cpf UNIQUE`.
- DDL `recepcao_atendimentos`: adicionadas colunas que o backend usa mas
  não estavam no DDL — `classificacao_risco` (enum), `observacoes`,
  `historia_clinica`, `hipotese_diagnostica`, `created_at`, `updated_at`.
  Coluna `criado_em` renomeada para `created_at`.

**Deploy (`DEPLOY_HMPCF_REMOTO.ps1`):**
- `hospital.db`: verificação virou `Log-Warn` (não aborta o deploy; usuário
  copia manualmente antes da migração).
- `CREATE DATABASE`: removido `LC_COLLATE 'Portuguese_Brazil.1252'` com
  `ENCODING 'UTF8'` — combinação incompatível que poderia rejeitar no PG 16.
- `$localIP`: null-check (exibe `SEM-IP-CONFIGURADO` em vez de `null`).
- `$migResult`: variável não usada removida.

**`backup_postgres.bat`:**
- `BACKUP_DIR`: corrigido para `C:\HMPCF\backups` (antes ficava em pasta
  separada na raiz do disco).
- Data: migrada de `%date:~6,4%` (dependente de locale) para
  `powershell Get-Date -Format 'yyyy-MM-dd'` (locale-safe).
- `mkdir` adicionado antes de usar o diretório.
- Limpeza de backups antigos via `Get-ChildItem` (substituiu `forfiles`
  que pode não existir em todos os Windows).

---

### Estrutura de pastas (produção)

```
C:\HMPCF\
  backups\          ← backups diários do PostgreSQL (antes: C:\hmpcf-backups)
  logs\             ← logs do serviço backend (antes: C:\hmpcf-logs)
  nssm\             ← binário do NSSM (antes: C:\nssm)
  legado\
    hospital.db     ← banco SQLite original (copiado manualmente, no .gitignore)
  backend\
  frontend\
  scripts\
```

---

### Boletim de Atendimento A4

Layout final aprovado. Especificação completa em `docs/BOLETIM_A4.md`.

**Resumo das medidas:**
- Margem: 5 mm topo/baixo, 6 mm laterais
- Labels: 15 px bold | Inputs: 15 px | Padding linha: 4 px
- Títulos de seção: 14 px bold, fundo `#d9d9d9`
- Cabeçalho: logo 70 px, nome hospital 16 px, prioridades 13 px
- Tabela risco: 13 px, padding 4 px
- Áreas de escrita: crescem igualmente (`flex: 1 1 0`) para preencher o
  restante da folha após os dados do paciente
- Placeholders (DD/MM/AAAA, 000.000.000-00) invisíveis na impressão

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
