# Deploy HMPCF — Guia de Implantação Hospitalar

**Sistema:** HMPCF — Hospital Municipal Pres. Café Filho  
**Ambiente:** Windows 10/11 — PC da Recepção — Uso 24h/dia — Rede LAN interna  
**Stack:** FastAPI + PostgreSQL 16 + React/Vite (build estático)  
**Sem Docker. Sem SQLite no novo sistema.**

---

## Índice

1. [Preparação da Máquina](#1-preparação-da-máquina)
2. [Estrutura de Pastas](#2-estrutura-de-pastas)
3. [Clonagem do Projeto](#3-clonagem-do-projeto)
4. [Configuração do PostgreSQL](#4-configuração-do-postgresql)
5. [Migração SQLite → PostgreSQL](#5-migração-sqlite--postgresql)
6. [Backend FastAPI em Produção](#6-backend-fastapi-em-produção)
7. [Frontend em Produção](#7-frontend-em-produção)
8. [Inicialização Automática](#8-inicialização-automática)
9. [Backup Automático](#9-backup-automático)
10. [Rede Interna](#10-rede-interna)
11. [Checklist Final](#11-checklist-final)

---

## 1. Preparação da Máquina

### 1.1 Verificar Windows

Abra o PowerShell como **Administrador** e execute:

```powershell
# Versão do Windows (precisa ser 10 ou 11)
winver

# Arquitetura (precisa ser x64)
[System.Environment]::Is64BitOperatingSystem
```

> Resultado esperado: `True`

---

### 1.2 Instalar PostgreSQL 16

1. Acesse: **https://www.postgresql.org/download/windows/**
2. Baixe o instalador **PostgreSQL 16** (versão x86-64)
3. Execute o instalador como Administrador
4. Durante a instalação:
   - **Installation Directory:** `C:\Program Files\PostgreSQL\16` (padrão)
   - **Data Directory:** `C:\Program Files\PostgreSQL\16\data` (padrão)
   - **Senha do superusuário (`postgres`):** defina e **ANOTE** — ex: `hmpcf2024`
   - **Porta:** `5432` (padrão)
   - **Locale:** `Portuguese, Brazil`
   - **Stack Builder:** pode desmarcar

5. Ao final, o PostgreSQL já estará instalado como **serviço Windows** com início automático.

Verificar:

```powershell
# Confirmar que o serviço está rodando
Get-Service postgresql*

# Resultado esperado:
# Status: Running | Name: postgresql-x64-16
```

Adicionar `pg_dump` ao PATH:

```powershell
# Verificar se psql está acessível
psql --version

# Se não estiver, adicionar manualmente ao PATH do sistema:
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    $env:PATH + ";C:\Program Files\PostgreSQL\16\bin",
    [System.EnvironmentVariableTarget]::Machine
)

# Fechar e reabrir o PowerShell após isso
```

---

### 1.3 Instalar Python 3.11+

1. Acesse: **https://www.python.org/downloads/windows/**
2. Baixe o **Python 3.11** (ou 3.12) — Windows installer 64-bit
3. Execute o instalador:
   - **MARCAR:** `Add Python to PATH`
   - **MARCAR:** `Install for all users`
   - Clicar em `Install Now`

Verificar:

```powershell
python --version
# Python 3.11.x

pip --version
# pip 23.x.x
```

---

### 1.4 Instalar Git

1. Acesse: **https://git-scm.com/download/windows**
2. Baixe e instale com as opções padrão
3. Em "Adjusting your PATH environment": escolha **Git from the command line and also from 3rd-party software**

Verificar:

```powershell
git --version
# git version 2.x.x
```

---

### 1.5 Instalar Node.js (apenas para o build — pode remover depois)

1. Acesse: **https://nodejs.org/en/download**
2. Baixe a versão **LTS** (ex: 20.x.x) — Windows Installer 64-bit
3. Instale com as opções padrão

Verificar:

```powershell
node --version
# v20.x.x

npm --version
# 10.x.x
```

---

### 1.6 Verificar todos os PATHs

Feche e reabra o PowerShell como Administrador, então:

```powershell
python --version
git --version
node --version
npm --version
psql --version
pg_dump --version
```

Todos devem responder sem erro de "comando não reconhecido".

---

## 2. Estrutura de Pastas

```
C:\
├── HMPCF\                        ← repositório git do projeto
│   ├── backend\
│   ├── frontend\
│   ├── scripts\
│   ├── legado\                   ← sistema antigo (não mexer)
│   ├── docs\
│   └── INICIAR.bat
│
├── hmpcf-backups\                ← backups diários do banco
│   ├── hmpcf_2026-05-28.sql
│   ├── hmpcf_2026-05-29.sql
│   └── ...
│
├── hmpcf-logs\                   ← logs do backend (criado pelo NSSM)
│   ├── backend.log
│   └── backend_err.log
│
├── nssm\                         ← gerenciador de serviços Windows
│   └── nssm.exe
│
└── Program Files\
    └── PostgreSQL\16\            ← banco de dados
        └── data\                 ← arquivos do banco (NÃO mexer)
```

---

## 3. Clonagem do Projeto

```powershell
# Criar pasta raiz
New-Item -ItemType Directory -Force -Path C:\HMPCF
cd C:\HMPCF

# Clonar o repositório
git clone https://github.com/fabiogomes95/HMPCF-Automation-System.git .

# Verificar branch correta
git branch
# * main

# Verificar arquivos principais
ls
# backend/  frontend/  scripts/  legado/  INICIAR.bat  ...
```

Se o projeto já foi clonado antes (atualização):

```powershell
cd C:\HMPCF
git pull origin main
git status
# On branch main, nothing to commit
```

Validar estrutura:

```powershell
Test-Path C:\HMPCF\backend\app\main.py        # True
Test-Path C:\HMPCF\frontend\src\App.jsx       # True
Test-Path C:\HMPCF\scripts\migrate_to_postgres.py  # True
Test-Path C:\HMPCF\legado\hospital.db         # True  ← banco legado SQLite
```

---

## 4. Configuração do PostgreSQL

### 4.1 Criar o banco de dados

Abra o **SQL Shell (psql)** que foi instalado com o PostgreSQL, ou use o PowerShell:

```powershell
psql -U postgres -h localhost
# Digite a senha que você definiu durante a instalação
```

Dentro do psql:

```sql
-- Criar o banco
CREATE DATABASE hmpcf
    WITH ENCODING 'UTF8'
    LC_COLLATE 'Portuguese_Brazil.1252'
    LC_CTYPE 'Portuguese_Brazil.1252'
    TEMPLATE template0;

-- Confirmar criação
\l

-- Sair
\q
```

---

### 4.2 Testar a conexão

```powershell
psql -U postgres -h localhost -d hmpcf -c "SELECT version();"
# Deve retornar a versão do PostgreSQL sem erros
```

---

### 4.3 Configurar o arquivo `.env` do backend

```powershell
cd C:\HMPCF\backend
copy .env.example .env
notepad .env
```

Preencher `.env` com:

```env
APP_NAME=HMPCF
ENVIRONMENT=production

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=hmpcf2024
POSTGRES_DB=hmpcf

DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_PRE_PING=true

CORS_ORIGINS=["*"]
```

> Substitua `hmpcf2024` pela senha real que você definiu.

---

### 4.4 Onde ficam os dados do PostgreSQL

Os dados do banco ficam em:

```
C:\Program Files\PostgreSQL\16\data\
```

**Nunca copie, mova ou exclua esta pasta manualmente.**  
O backup correto é feito via `pg_dump` (ver seção 9).

---

## 5. Migração SQLite → PostgreSQL

> Esta etapa migra os dados do sistema legado (`legado/hospital.db`) para o PostgreSQL.  
> O banco SQLite **não é modificado** — é aberto em modo leitura.

### 5.1 Criar ambiente virtual para os scripts de migração

```powershell
cd C:\HMPCF\scripts

python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install psycopg2-binary python-dotenv
```

---

### 5.2 Configurar `.env` para migração

```powershell
# Criar .env na pasta scripts/
notepad C:\HMPCF\scripts\.env
```

Conteúdo:

```env
SQLITE_PATH=../legado/hospital.db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hmpcf
POSTGRES_USER=postgres
POSTGRES_PASSWORD=hmpcf2024
LOG_FILE=migration.log
BATCH_SIZE=500
```

---

### 5.3 Criar as tabelas no PostgreSQL

Antes de migrar, as tabelas precisam existir. Execute:

```powershell
cd C:\HMPCF\scripts
.venv\Scripts\python recreate_pacientes.py --dry-run
```

Verifique o output — deve mostrar contagens e zero erros.

Se OK, execute de verdade:

```powershell
.venv\Scripts\python recreate_pacientes.py
```

> Este script cria as tabelas `pacientes` e `recepcao_atendimentos`  
> com a estrutura correta para o BPA/SUS.

---

### 5.4 Simulação da migração (dry-run)

```powershell
cd C:\HMPCF\scripts
.venv\Scripts\python migrate_to_postgres.py --dry-run
```

Output esperado:

```
[INFO] Conectando ao SQLite: ../legado/hospital.db (modo leitura)
[INFO] Pacientes no SQLite: 30.496
[INFO] Únicos para migrar: 29.242
[INFO] Duplicatas detectadas: 1.254
[INFO] Atendimentos no SQLite: 11.758
[INFO] DRY-RUN: nenhum dado gravado no PostgreSQL
[INFO] 0 erros encontrados
```

Se houver erros, revise o `.env` antes de continuar.

---

### 5.5 Migração real

```powershell
.venv\Scripts\python migrate_to_postgres.py
```

O script:
- Lê o SQLite em modo somente-leitura
- Valida CPF (dígitos verificadores) e CNS (mod 11)
- Remove duplicatas por CPF e CNS
- Corrige datas inválidas
- Migra pacientes em lotes de 500
- Migra atendimentos históricos
- Gera `migration.log` com todo o processo
- É idempotente: pode ser executado novamente sem criar duplicatas

---

### 5.6 Validar a migração

```powershell
psql -U postgres -h localhost -d hmpcf -c "
SELECT
    (SELECT COUNT(*) FROM pacientes)          AS pacientes,
    (SELECT COUNT(*) FROM recepcao_atendimentos) AS atendimentos;
"
```

Resultado esperado:

```
 pacientes | atendimentos
-----------+--------------
    29242  |       11687
```

Verificar o log:

```powershell
notepad C:\HMPCF\scripts\migration.log
# Procure por linhas [ERROR] ou [WARNING]
```

---

### 5.7 O que fazer se precisar re-migrar

Se precisar recomeçar do zero (apaga tudo e re-migra):

```powershell
.venv\Scripts\python migrate_to_postgres.py --truncate
```

> **ATENÇÃO:** `--truncate` apaga todos os dados do PostgreSQL antes de migrar.  
> Use apenas se tiver certeza absoluta de que o PostgreSQL está vazio ou com dados incorretos.

---

## 6. Backend FastAPI em Produção

### 6.1 Criar ambiente virtual

```powershell
cd C:\HMPCF\backend
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

Verificar instalação:

```powershell
.venv\Scripts\python -c "import fastapi, uvicorn, sqlalchemy, asyncpg; print('OK')"
# OK
```

---

### 6.2 Verificar variáveis de ambiente

```powershell
cd C:\HMPCF\backend
.venv\Scripts\python -c "
from app.core.config import settings
print('DB:', settings.database_url[:40], '...')
print('ENV:', settings.ENVIRONMENT)
print('APP:', settings.APP_NAME)
"
```

Output esperado:

```
DB: postgresql+asyncpg://postgres:***@localhost:5432/hmpcf ...
ENV: production
APP: HMPCF
```

---

### 6.3 Iniciar backend manualmente (teste)

```powershell
cd C:\HMPCF\backend
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Aguardar:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

### 6.4 Criar as contas de acesso (uma vez só, por instalação)

Desde 04/09/2026, `/api/v1/*` exige login — sem sessão válida,
qualquer chamada volta `401`. As tabelas `usuarios`/`sessoes` são criadas
por um script standalone (o projeto ainda não usa Alembic):

```powershell
cd C:\HMPCF\backend
.venv\Scripts\python scripts\criar_tabelas_auth.py
# OK: tabelas 'usuarios' e 'sessoes' garantidas (criadas agora ou já existentes).
```

Depois, criar as contas de papel (uma por área — não é login por pessoa
nesta versão). A senha é digitada no prompt (nunca em argumento de linha
de comando):

```powershell
.venv\Scripts\python scripts\gerenciar_usuarios.py criar --username recepcao    --role recepcao
.venv\Scripts\python scripts\gerenciar_usuarios.py criar --username coordenacao --role coordenacao
.venv\Scripts\python scripts\gerenciar_usuarios.py criar --username bpa         --role bpa
```

> `coordenacao` e `bpa` já ficam prontas no banco pra quando o login
> chegar no dashboard/BPA (próxima etapa) — na recepção (`frontend/`),
> por enquanto, só a conta `recepcao` é usada de fato.

Pra trocar senha depois (sem precisar redeploy) ou conferir quais contas
existem:

```powershell
.venv\Scripts\python scripts\gerenciar_usuarios.py resetar-senha --username recepcao
.venv\Scripts\python scripts\gerenciar_usuarios.py listar
```

---

### 6.5 Testar o backend

Abra o navegador ou outro PowerShell:

```powershell
# Health check (não exige login)
Invoke-WebRequest http://localhost:8001/health | Select -Expand Content
# {"status":"ok","app":"HMPCF","env":"production"}

# Sem login -> 401 (esperado)
Invoke-WebRequest "http://localhost:8001/api/v1/pacientes?page_size=1"
# 401 Unauthorized

# Login guardando a sessão numa variável, depois reaproveitando o cookie
$sessao = $null
Invoke-WebRequest -Uri "http://localhost:8001/api/v1/auth/login" -Method Post `
  -ContentType "application/json" -Body '{"username":"recepcao","password":"SUA_SENHA"}' `
  -SessionVariable sessao | Select -Expand Content
# {"username":"recepcao","role":"recepcao"}

Invoke-WebRequest "http://localhost:8001/api/v1/pacientes?page_size=1" -WebSession $sessao | Select -Expand Content
# {"items":[...],"total":29242,...}
```

> Em produção (`ENVIRONMENT=production`), a rota `/docs` não existe por segurança.  
> Para verificar os endpoints, mude temporariamente para `ENVIRONMENT=development` e acesse  
> `http://localhost:8001/docs`.

Encerrar o teste:

```
Ctrl+C
```

---

## 7. Frontend em Produção

### 7.1 Instalar dependências

```powershell
cd C:\HMPCF\frontend
npm install
```

---

### 7.2 Build de produção

```powershell
npm run build
```

Output esperado:

```
vite v5.x.x building for production...
✓ 93 modules transformed.
dist/index.html                   0.48 kB │ gzip: 0.32 kB
dist/assets/index-[hash].css     13.69 kB │ gzip: 3.39 kB
dist/assets/vendor-[hash].js    140.87 kB │ gzip: 45.84 kB
dist/assets/index-[hash].js      74.23 kB │ gzip: 26.01 kB
✓ built in ~1s
```

Verificar:

```powershell
Test-Path C:\HMPCF\frontend\dist\index.html    # True
Test-Path C:\HMPCF\frontend\dist\assets        # True
```

---

### 7.3 Frontend servido pelo FastAPI

O backend já está configurado para servir o `dist/` automaticamente.  
Quando o backend sobe na porta 8001:

- `http://localhost:8001/` → abre o HMPCF (React)
- `http://localhost:8001/api/v1/...` → API FastAPI
- `http://localhost:8001/health` → health check

**Não é necessário o Vite dev server nem Node.js rodando continuamente.**  
Node.js foi usado apenas para o `npm run build`.

---

### 7.4 Testar o frontend

```powershell
# Backend ainda precisa estar rodando (da seção 6.3)
start http://localhost:8001
```

O HMPCF deve abrir no navegador com a tela de Recepção.

Testar:
- [ ] Busca por CPF carrega paciente existente
- [ ] Busca por CPF inexistente mostra "+ Novo paciente"
- [ ] Aba Histórico: busca por nome retorna resultados
- [ ] Botão "Registrar Atendimento" funciona
- [ ] Impressão (Ctrl+P) mostra apenas o boletim

---

## 8. Inicialização Automática

O objetivo é: **ligar o PC → HMPCF já está rodando**, sem ninguém precisar abrir terminal.

O PostgreSQL já inicia automaticamente (é um serviço Windows instalado pelo instalador).  
O backend precisa ser registrado como serviço Windows via **NSSM**.

---

### 8.1 Baixar e instalar NSSM

1. Acesse: **https://nssm.cc/download**
2. Baixe a versão mais recente (Win64)
3. Extraia o arquivo `.zip`
4. Copie `nssm.exe` para `C:\nssm\nssm.exe`

Verificar:

```powershell
C:\nssm\nssm.exe version
# NSSM 2.24 2014-08-31
```

---

### 8.2 Instalar o backend como serviço

```powershell
# Executar como Administrador
cd C:\HMPCF\scripts
.\instalar_servico.bat
```

O script instala o serviço `HMPCF-Backend` com:
- Início automático ao ligar o Windows
- Reinício automático em caso de falha (após 5 segundos)
- Logs em `C:\hmpcf-logs\backend.log`

Verificar:

```powershell
Get-Service HMPCF-Backend
# Status: Running
```

---

### 8.3 Gerenciar o serviço

```powershell
# Parar
net stop HMPCF-Backend

# Iniciar
net start HMPCF-Backend

# Reiniciar (após atualização)
net stop HMPCF-Backend; net start HMPCF-Backend

# Ver status
Get-Service HMPCF-Backend

# Ver logs em tempo real
Get-Content C:\hmpcf-logs\backend.log -Wait -Tail 50
```

---

### 8.4 Testar inicialização automática

```powershell
# Reiniciar o PC
Restart-Computer

# Após a reinicialização, verificar se o serviço subiu:
Get-Service HMPCF-Backend
# Running

# Abrir o HMPCF
start http://localhost:8001
```

---

### 8.5 Atualizar o sistema (deploy de nova versão)

```powershell
cd C:\HMPCF

# Baixar atualizações
git pull origin main

# Rebuild do frontend (se houver mudanças no frontend)
cd frontend
npm run build
cd ..

# Reiniciar o serviço
net stop HMPCF-Backend
net start HMPCF-Backend

# Verificar
start http://localhost:8001
```

---

## 9. Backup Automático

O backup roda via `scripts\windows\backup_postgres.bat`: gera o dump com
`pg_dump` (senha lida direto de `backend\.env`, nada de `PGPASSWORD` manual),
e em seguida **criptografa o dump com AES-256** via
`scripts\windows\encrypt_backup.ps1` — o `.sql` em claro é apagado, só fica
o `.sql.enc`.

### 9.1 Configurar a senha de criptografia do backup

Crie o arquivo (uma vez só, nunca versionado — já está no `.gitignore`):

```powershell
"SUA_SENHA_FORTE_AQUI" | Out-File -Encoding utf8 -NoNewline `
    C:\HMPCF-Automation-System\scripts\windows\.backup_passphrase
```

> **Anote essa senha em outro lugar também** (gerenciador de senhas, papel).
> Sem ela, os backups antigos não podem ser restaurados — nem por quem tem
> acesso total ao servidor.

---

### 9.2 Testar o backup manualmente

```powershell
C:\HMPCF-Automation-System\scripts\windows\backup_postgres.bat
```

Output esperado:

```
Iniciando backup...
[OK] Backup: C:\HMPCF\backups\hmpcf_2026-07-02.sql
Criptografando backup...
[OK] Backup criptografado: C:\HMPCF\backups\hmpcf_2026-07-02.sql.enc
```

Verificar:

```powershell
ls C:\HMPCF\backups\
# hmpcf_2026-07-02.sql.enc  (~10-50 MB) — so o .enc deve existir, sem .sql em claro
```

---

### 9.3 Agendar backup diário automático

```powershell
# Executar como Administrador
powershell -ExecutionPolicy Bypass -File C:\HMPCF-Automation-System\scripts\windows\agendar_backup.ps1
```

Output:

```
Backup diario agendado para 23:00
Backups criptografados salvos em: C:\HMPCF\backups\ (.sql.enc)
```

O backup roda todos os dias às 23:00 e mantém os últimos 30 dias.

---

### 9.4 Verificar o agendamento

```powershell
Get-ScheduledTask -TaskName "HMPCF-Backup-Diario"
# State: Ready

# Executar manualmente para testar
Start-ScheduledTask -TaskName "HMPCF-Backup-Diario"
Start-Sleep 5
ls C:\HMPCF\backups\
```

---

### 9.5 Restaurar backup (emergência)

Se o banco for corrompido ou perdido:

```powershell
# 1. Descriptografar o backup mais recente
$backupEnc = (ls C:\HMPCF\backups\*.sql.enc | Sort LastWriteTime | Select -Last 1).FullName
powershell -File C:\HMPCF-Automation-System\scripts\windows\decrypt_backup.ps1 -Path $backupEnc
$backup = $backupEnc -replace '\.enc$', ''

# 2. Recriar o banco vazio
psql -U postgres -c "DROP DATABASE IF EXISTS hmpcf;"
psql -U postgres -c "CREATE DATABASE hmpcf ENCODING 'UTF8';"

# 3. Restaurar
psql -U postgres -d hmpcf -f $backup

# 4. Verificar
psql -U postgres -d hmpcf -c "SELECT COUNT(*) FROM pacientes;"

# 5. Apagar o .sql em claro gerado no passo 1 (nao deixar dado sensivel solto)
Remove-Item $backup -Force
```

---

## 10. Rede Interna

### 10.1 Descobrir o IP do PC servidor

```powershell
ipconfig
# Procure por "IPv4 Address" da placa de rede principal
# Exemplo: 192.168.1.100
```

Anotar o IP: `_______________________`

---

### 10.2 Liberar firewall para a porta 8001

```powershell
# Como Administrador
New-NetFirewallRule `
    -DisplayName "HMPCF Backend" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8001 `
    -Action Allow `
    -Profile Domain,Private
```

Verificar:

```powershell
Get-NetFirewallRule -DisplayName "HMPCF Backend"
# Enabled: True | Action: Allow
```

---

### 10.3 Testar acesso pela rede

De **outro PC na mesma rede**:

```powershell
# Substitua pelo IP do servidor
start http://192.168.1.100:8001
```

O HMPCF deve abrir normalmente no navegador.

---

### 10.4 URLs finais do sistema

| Acesso | URL |
|--------|-----|
| No próprio PC servidor | `http://localhost:8001` |
| De outro PC na rede | `http://192.168.1.100:8001` (usar IP real) |
| Health check | `http://192.168.1.100:8001/health` |
| API (dev only) | `http://192.168.1.100:8001/docs` |

> **Dica:** Fixe o IP do servidor no roteador (DHCP reservation) para que o IP não mude.

---

## 11. Checklist Final de Produção

Execute este checklist após a implantação e a cada atualização importante.

### 11.1 Infraestrutura

- [ ] PostgreSQL 16 instalado como serviço Windows
- [ ] Serviço PostgreSQL em estado `Running`
- [ ] Banco `hmpcf` criado e acessível
- [ ] Backend `HMPCF-Backend` instalado como serviço Windows
- [ ] Serviço `HMPCF-Backend` em estado `Running`
- [ ] PC reiniciou e ambos os serviços subiram automaticamente

### 11.2 Banco de dados

- [ ] `SELECT COUNT(*) FROM pacientes;` → ~29.000 registros
- [ ] `SELECT COUNT(*) FROM recepcao_atendimentos;` → ~11.000 registros
- [ ] Nenhum erro crítico no `migration.log`
- [ ] Backup manual executado com sucesso
- [ ] Backup agendado configurado no Task Scheduler
- [ ] `scripts\criar_tabelas_auth.py` rodado — tabelas `usuarios`/`sessoes` existem
- [ ] Contas `recepcao`/`coordenacao`/`bpa` criadas (`scripts\gerenciar_usuarios.py listar`)

### 11.3 Backend

- [ ] `http://localhost:8001/health` → `{"status":"ok",...}`
- [ ] `http://localhost:8001/api/v1/pacientes?page_size=1` **sem** login → `401`
- [ ] Login em `/api/v1/auth/login` com a conta `recepcao` → `200` + cookie de sessão
- [ ] `http://localhost:8001/api/v1/pacientes?page_size=1` **com** o cookie → lista pacientes
- [ ] Logs em `C:\hmpcf-logs\backend.log` sem erros críticos

### 11.4 Frontend

- [ ] `http://localhost:8001/` abre a tela de **login** antes de qualquer coisa
- [ ] Login com usuário/senha errados mostra mensagem de erro, não trava a tela
- [ ] Login correto (conta `recepcao`) abre a tela de Recepção
- [ ] Botão "Sair" desloga e volta pra tela de login
- [ ] Busca por CPF de paciente existente preenche o formulário
- [ ] Busca por CPF inexistente mostra "+ Novo paciente"
- [ ] Sexo, nome, data de nascimento são obrigatórios (validação ativa)
- [ ] Botão "Registrar Atendimento" registra e desabilita até "Limpar"
- [ ] Botão "Limpar" reseta o formulário e foca no campo CPF
- [ ] Botão "Imprimir" abre o diálogo de impressão com layout correto
- [ ] Botão "Família" copia endereço do paciente anterior
- [ ] Aba Histórico: busca por nome retorna resultados corretamente
- [ ] Histórico: expandir linha mostra atendimentos do paciente
- [ ] Histórico: botão "Editar" abre o atendimento na recepção

### 11.5 Rede

- [ ] Acesso via `http://IP_DO_SERVIDOR:8001` funciona de outro PC
- [ ] Regra de firewall criada para porta 8001
- [ ] IP do servidor anotado e comunicado às estações da rede

### 11.6 Legado

- [ ] Pasta `legado/` intacta — sistema antigo não foi modificado
- [ ] `legado/hospital.db` presente (banco SQLite original)
- [ ] Sistema legado (se ainda em uso) opera normalmente em paralelo

---

## Referência rápida — Comandos do dia a dia

> O backend roda como **Serviço do Windows via NSSM**, nome real
> `HMPCF-Backend-Svc` (não confundir com a Tarefa Agendada de mesmo nome
> parecido, que fica desativada — ver `docs/HISTORICO.md` sobre a
> consolidação em 02/07/2026).

```powershell
# Ver status dos serviços
Get-Service postgresql-x64-16, HMPCF-Backend-Svc, HMPCF-Dashboard-Svc

# Reiniciar backend (após atualização)
Restart-Service HMPCF-Backend-Svc

# Atualizar o sistema
cd C:\HMPCF-Automation-System
git pull origin main
cd frontend; npm run build; cd ..
Restart-Service HMPCF-Backend-Svc

# Fazer backup agora
C:\HMPCF-Automation-System\scripts\windows\backup_postgres.bat

# Ver logs do backend
Get-Content C:\hmpcf-logs\backend.log -Tail 50

# Conectar ao banco
psql -U postgres -d hmpcf

# Contar registros
psql -U postgres -d hmpcf -c "SELECT COUNT(*) FROM pacientes;"
```

---

*Documento gerado em 2026-05-28. Atualizar a cada mudança de infraestrutura.*
