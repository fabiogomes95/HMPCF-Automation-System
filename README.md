# HMPCF Automation System

> Sistema de automação hospitalar para recepção digital, painel gerencial em
> tempo real e faturamento BPA/SUS. Desenvolvido para o Hospital Municipal
> Pres. Café Filho — Extremoz/RN, Brasil.

Arquitetura moderna com **FastAPI + PostgreSQL + React/Vite** para a recepção,
um **painel gerencial em Streamlit** para coordenação/TI, e um serviço
**Flask + Firebird** dedicado à geração dos arquivos de faturamento BPA/SUS.

---

## Visão Geral

O HMPCF Automation System é composto por três frentes independentes, todas
lendo o mesmo PostgreSQL como fonte de verdade:

1. **Recepção digital** (`backend/` + `frontend/`) — cadastro e atendimento de
   pacientes, em produção no terminal da recepção do hospital.
2. **Painel gerencial** (`dashboard/`) — visão em tempo real para
   coordenadores e TI: histórico diário, busca de paciente e importação de
   planilhas manuais. Processo independente, somente leitura por padrão, não
   interfere na recepção.
3. **Faturamento BPA/SUS** (`bpa/`) — aplicação Flask separada que gera os
   arquivos posicionais BPA-I (um por profissional/categoria, por
   competência) a partir dos atendimentos do PostgreSQL, migrando os dados
   para a base Firebird (`BPAMAG.GDB`) exigida pelo BPA Magnético do
   Ministério da Saúde.

O **sistema legado** (`legado/`, Python/Eel/SQLite) foi **descontinuado em
02/07/2026** — permanece no repositório apenas como referência histórica e
não recebe mais manutenção nem deploy.

---

## Status

| Módulo | Situação |
|--------|----------|
| Recepção digital (FastAPI + React) | **Em produção** |
| Painel gerencial (Streamlit) | **Em produção** |
| Faturamento BPA/SUS (geração de arquivo posicional) | **Em produção** |
| Importação de planilhas manuais (deduplicação, correção de fuso/turno) | **Em produção** |
| Início automático (Tarefa Agendada + watchdog) | **Configurado** |
| Autenticação / autorização na API | **A fazer** — sistema pensado para rede local isolada do hospital; ver [Segurança](#segurança-e-limitações-conhecidas) |
| Testes automatizados (backend) | 21 testes |
| Testes automatizados (frontend / dashboard / bpa) | Não há |
| Sistema legado (Firebird/Eel) | **Descontinuado** — mantido só como referência |

---

## Arquitetura

```
📦 HMPCF-Automation-System
 ┣ 📂 backend/                       # API FastAPI — recepção digital
 ┃  ┗ 📂 app/
 ┃     ┣ 📜 main.py                  # Entrypoint (lifespan, CORS, handlers)
 ┃     ┣ 📂 core/                    # Config (pydantic-settings) + exceções
 ┃     ┣ 📂 database/                # Engine async, SessionLocal
 ┃     ┣ 📂 models/                  # SQLAlchemy ORM (pacientes, atendimentos)
 ┃     ┣ 📂 schemas/                 # Pydantic v2
 ┃     ┣ 📂 repositories/            # Queries isoladas
 ┃     ┣ 📂 services/                # Regras de negócio
 ┃     ┗ 📂 api/v1/endpoints/        # Pacientes · Recepção · Terminal
 ┃  ┗ 📂 tests/                      # 21 testes (pytest)
 ┣ 📂 frontend/                      # React + Vite — terminal de digitação
 ┣ 📂 dashboard/                     # Streamlit — painel gerencial (TI/coordenação)
 ┃  ┣ 📜 app.py                      # KPIs, gráficos (volume, sexo, idade, bairros)
 ┃  ┣ 📜 db.py                       # Conexão somente leitura + utilitários compartilhados
 ┃  ┣ 📜 bpa_gerador.py              # Lógica de geração BPA-I (reaproveitada por bpa/)
 ┃  ┣ 📜 importador.py               # Parser e importação de planilhas manuais
 ┃  ┗ 📂 pages/
 ┃     ┣ 📜 1_Historico_Diario.py    # Histórico do dia, filtrável (hoje/ontem/data)
 ┃     ┣ 📜 2_Importar_Planilha_Mensal.py  # Upload .tsv → compara e importa faltantes
 ┃     ┗ 📜 3_Buscar_Paciente.py     # Busca por nome/CPF/CNS → histórico completo
 ┣ 📂 bpa/                           # Flask — geração BPA-I e migração PG→Firebird
 ┃  ┗ 📜 app.py                      # Digitação, geração do BPA-I, migração (usa dashboard/bpa_gerador.py)
 ┣ 📂 docs/                          # Arquitetura, histórico, guias de instalação/deploy
 ┣ 📂 scripts/                       # deploy/, windows/ (launchers, backup, serviço), bpa/, importacao/, migrations/
 ┣ 📂 legado/                        # Sistema original — descontinuado, mantido como referência
 ┣ 📜 docker-compose.yml             # PostgreSQL + pgAdmin + backend (uso local/desenvolvimento)
 ┗ 📜 INICIAR.bat                    # Launcher da recepção (backend + frontend), produção
```

---

## Como Rodar

### Recepção (Windows, produção)

```bat
INICIAR.bat
```

Sobe o backend (`uvicorn`, porta 8001, que também serve o frontend buildado
em `frontend/dist/`) e abre o navegador. Registrado como Tarefa Agendada
(`HMPCF-Backend`) — inicia no boot e reinicia automaticamente se cair
(watchdog em `scripts/windows/watchdog_backend.vbs`).

### Painel Gerencial (Streamlit)

```bash
cd dashboard
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

Sobe em `http://localhost:8502` (rede local: `http://<ip-da-maquina>:8502`).
Launcher em `scripts/windows/ABRIR_DASHBOARD.bat`, também registrado como
Tarefa Agendada, independente do backend.

### Faturamento BPA/SUS (Flask)

```bash
cd bpa
python app.py
```

Sobe em `http://localhost:8503` (ajustável). Reaproveita `dashboard/venv` e
`dashboard/bpa_gerador.py`; exige acesso ao PostgreSQL (leitura dos
atendimentos) e à base Firebird local do BPA Magnético.

### Docker (banco de dados local, desenvolvimento)

```bash
# Define as senhas obrigatorias antes de subir (nao ha default fraco)
cp .env.example .env   # edite POSTGRES_PASSWORD e PGADMIN_PASSWORD

docker compose up -d
```

Portas do compose ficam bindadas em `127.0.0.1` por padrão (não expostas na
rede) — ajuste conforme necessário para o seu ambiente de desenvolvimento.

| Serviço | Porta | Acesso |
|---------|-------|--------|
| Backend API (recepção) | 8001 | http://localhost:8001/docs *(desabilitado em produção)* |
| Painel Gerencial | 8502 | http://localhost:8502 |
| BPA/SUS | 8503 | http://localhost:8503 |
| Frontend (dev) | 5173 | http://localhost:5173 |
| PostgreSQL (Docker) | 5432 | 127.0.0.1 apenas |
| pgAdmin (Docker) | 5050 | 127.0.0.1 apenas |

### Configuração

```bash
cp backend/.env.example backend/.env
# edite com suas credenciais — o dashboard reaproveita esse mesmo .env
```

`.env` nunca é versionado (`.gitignore` cobre `.env` e `**/.env`). Nunca
commitar senhas reais em scripts ou documentação — os scripts de
deploy/backup pedem a senha interativamente ou a leem do `.env`.

---

## Painel Gerencial (Dashboard)

Aplicação **Streamlit independente**, com seu próprio ambiente virtual e
porta — não compartilha processo, código ou dependências com o backend da
recepção. Lê o PostgreSQL em modo somente leitura por padrão; escreve apenas
nas telas explicitamente destinadas a isso (importação de planilha), sempre
com confirmação manual antes de gravar.

**Painel principal** — KPIs (hoje / semana / mês / total), volume diário,
distribuição por sexo, faixa etária e bairro de origem.

**Histórico Diário** — lista completa de atendimentos de um dia específico,
com nome, CPF, CNS, nascimento, idade, sexo, endereço e telefone.

**Buscar Paciente** — pesquisa por nome, CPF ou CNS, retornando todas as
entradas (data e horário) daquele paciente no sistema.

**Importar Planilha Mensal** — compara a planilha manual de plantão (`.tsv`)
com o banco e importa só os atendimentos que faltam (quando o plantão
registra no papel mas não digita no sistema). Trata os casos reais já
encontrados em produção:
- Deduplicação por paciente: mesmo registro de plantão ou horário a poucos
  minutos de distância → mantém só o lançamento mais recente.
- Correção automática de erro de digitação no ano do cabeçalho do plantão.
- Atendimentos de madrugada sob plantão noturno contam para o dia seguinte
  (mesma regra usada pela digitação real da recepção).
- Linhas com formato inesperado (ex: documento digitado no campo errado) são
  isoladas para revisão manual, nunca importadas silenciosamente.

---

## Faturamento BPA/SUS

Aplicação Flask (`bpa/app.py`) responsável por:

- **Digitação/consulta** de dados complementares exigidos pelo BPA Magnético
  que não fazem parte da recepção digital.
- **Geração do BPA-I** — um arquivo por profissional/categoria, por
  competência, salvo em `BPA_LOTES_DIR`, com folha/sequência contínua e
  nacionalidade fixa.
- **Migração PostgreSQL → Firebird** — completa cadastros na base Firebird
  (`BPAMAG.GDB`) a partir dos atendimentos reais do PostgreSQL, com validação
  de CPF antes de migrar.

---

## Banco de Dados

PostgreSQL como única fonte de verdade. Migrations versionadas via Alembic.

```bash
cd backend

# Aplicar migrations
alembic upgrade head

# Nova migration após alterar models
alembic revision --autogenerate -m "descricao"
```

---

## Endpoints Ativos (Backend)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/pacientes` | Listar pacientes |
| POST | `/api/v1/pacientes` | Criar paciente |
| GET | `/api/v1/pacientes/{id}` | Buscar por ID |
| GET | `/api/v1/recepcao` | Listar atendimentos |
| POST | `/api/v1/recepcao` | Registrar atendimento |
| GET | `/api/v1/recepcao/pacientes/agrupado?q=...` | Busca agrupada com histórico |
| GET | `/api/v1/recepcao/paciente/{id}` | Histórico completo do paciente |
| GET | `/api/v1/terminal` | Status do sistema |
| GET | `/health` | Health check (sem autenticação, sem dados sensíveis) |

Documentação interativa (apenas fora de produção): `http://localhost:8001/docs`

---

## Testes

```bash
cd backend
pytest tests/ -v
```

21 testes cobrindo pacientes, recepção e terminal (backend apenas — frontend,
dashboard e bpa/ ainda não têm suíte automatizada).

---

## Segurança e Limitações Conhecidas

Este sistema foi desenhado para operar dentro da **rede local isolada do
hospital**, não exposto à internet. Pontos relevantes para quem for
implantar ou operar:

- **Sem autenticação/autorização na API** ainda — qualquer dispositivo com
  acesso à rede local do backend pode ler/escrever atendimentos. Compensar
  com segmentação de rede adequada (perfil de firewall `Domain`/`Private`,
  nunca `Public`, e VLAN dedicada se possível) até autenticação ser
  implementada.
- **Segredos vivem só em `.env`** (nunca em scripts ou docs versionados) —
  ao gerar uma senha nova, evite caracteres que sejam delimitadores de URL
  (`@ : / ? #`) em strings de conexão, ou garanta que o código faça
  URL-encode antes de montar a connection string.
- **Dados sensíveis (CPF, CNS, endereço, dados de saúde)** — evite logar
  esses valores em texto puro em scripts de importação/migração; prefira
  logar apenas identificadores técnicos (ID interno) em caso de erro.
- **Backups** (`scripts/windows/backup_postgres.bat`) geram dump em texto
  puro localmente — combine com controle de acesso ao diretório de backup e
  rotação/expurgo (já implementado, 30 dias).

Contribuições que fecham essas lacunas (auth de sessão, RBAC básico,
criptografia de backup) são bem-vindas.

---

## Legado

O sistema original (`legado/`, Python/Eel/SQLite) foi **oficialmente
descontinuado em 02/07/2026**. Permanece no repositório apenas como
referência histórica e fallback documental — não recebe deploy nem
manutenção. Consulte `legado/passo_a_passo.md` se precisar entender como ele
operava.

---

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação
em produção sem autorização explícita do autor.
