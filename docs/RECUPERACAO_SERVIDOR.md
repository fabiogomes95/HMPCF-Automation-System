# Recuperação do servidor — montar o sistema do zero

Para quando o PC da recepção (servidor, `192.168.1.29`, `DESKTOP-9C4S1CO`)
morrer, for trocado ou formatado. Leva algumas horas; o que não pode faltar é
o **backup** e os **dois segredos** abaixo.

## Antes de tudo: o que precisa existir FORA do servidor

| O quê | Onde fica no servidor | Sem ele… |
|---|---|---|
| Backup criptografado `hmpcf_AAAA-MM-DD.sql.enc` | `C:\HMPCF\backups` e Google Drive (*Computadores → backups_nuvem*; antes de 24/09/2026: *Meu Drive → HMPCF-Backups*) | perde-se o banco |
| **Senha de criptografia do backup** | `scripts\servidor\.backup_passphrase` | o backup não abre |
| Senha do usuário `bpa_leitura` | `C:\HMPCF\bpa_leitura_credenciais.txt` (e no `bpa\.env` dos notebooks) | os notebooks do BPA não conectam (dá pra criar outra e trocar nos 2 `bpa\.env`) |

A senha de criptografia **tem que estar guardada fora do servidor** (papel no
cofre, gerenciador de senhas) — ela nunca vai pro git nem pro Google Drive.

## 1. Programas

- Windows 10/11 com **IP fixo `192.168.1.29`** (os notebooks do BPA e o
  `BPA_ORIGENS_PERMITIDAS` usam esse endereço). Se o IP mudar, ajuste
  `BPA_ORIGENS_PERMITIDAS` no `bpa\.env` dos notebooks.
- **PostgreSQL 16** (instalador oficial, serviço `postgresql-x64-16`). A senha
  do usuário `postgres` vai só no `backend\.env`.
- **Python 3.12+**, **Git**, **Node.js 18+** (para compilar as telas).
- **Google Drive para computador**, logado na conta do hospital.

## 2. Código e segredos

```powershell
git clone https://github.com/fabiogomes95/HMPCF-Automation-System C:\HMPCF-Automation-System
cd C:\HMPCF-Automation-System
copy backend\.env.example backend\.env      # preencha POSTGRES_PASSWORD e ENVIRONMENT=production
# recrie scripts\servidor\.backup_passphrase com a senha de criptografia (1 linha)
```

## 3. Banco de dados

```powershell
$env:PGPASSWORD = "<senha do postgres>"
$pg = "C:\Program Files\PostgreSQL\16\bin"
& "$pg\psql" -U postgres -c "CREATE DATABASE hmpcf"
& "$pg\psql" -U postgres -c "ALTER SYSTEM SET timezone = 'America/Sao_Paulo'"   # vale após reiniciar o serviço
# o usuário dos notebooks vem ANTES do restore, pra ele já receber as permissões
& "$pg\psql" -U postgres -c "CREATE ROLE bpa_leitura LOGIN PASSWORD '<senha do bpa_leitura>'"

powershell -File scripts\servidor\decrypt_backup.ps1 -Path C:\HMPCF\backups\hmpcf_AAAA-MM-DD.sql.enc
& "$pg\psql" -U postgres -d hmpcf -f C:\HMPCF\backups\hmpcf_AAAA-MM-DD.sql
del C:\HMPCF\backups\hmpcf_AAAA-MM-DD.sql     # o .sql em claro não fica no disco
```

Rede (`C:\Program Files\PostgreSQL\16\data`):

- `postgresql.conf`: `listen_addresses = '*'`
- `pg_hba.conf`: `postgres` só local; pela rede **só** o `bpa_leitura`:
  `host  hmpcf  bpa_leitura  0.0.0.0/0  scram-sha-256`
- Firewall: liberar a porta 5432 (BPA) e a 8001 (sistema) na rede privada.
- Reiniciar o serviço `postgresql-x64-16`.

## 4. Backend e telas

```powershell
cd C:\HMPCF-Automation-System\backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m alembic current      # o backup já traz a versão; tem que mostrar (head)
.venv\Scripts\python -m alembic upgrade head

cd ..\frontend
npm ci
npm run build                                 # gera frontend\dist, servido pelo backend
```

## 5. Serviços (sobem sozinhos com o Windows)

Como administrador, na pasta do sistema:

```powershell
$n = "C:\HMPCF-Automation-System\nssm\nssm.exe"   # nssm.exe fora do git: baixe em nssm.cc
& $n install HMPCF-Backend-Svc "C:\HMPCF-Automation-System\backend\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port 8001"
& $n set HMPCF-Backend-Svc AppDirectory C:\HMPCF-Automation-System\backend
& $n set HMPCF-Backend-Svc AppStdout C:\HMPCF-Automation-System\backend\nssm_backend.log
& $n set HMPCF-Backend-Svc AppStderr C:\HMPCF-Automation-System\backend\nssm_backend.log
& $n set HMPCF-Backend-Svc AppRotateFiles 1
& $n set HMPCF-Backend-Svc AppRotateOnline 0       # 1 trava o serviço em StopPending ao reiniciar
& $n set HMPCF-Backend-Svc AppRotateBytes 10485760
& $n start HMPCF-Backend-Svc

powershell -ExecutionPolicy Bypass -File scripts\servidor\instalar_servico_backup.ps1
powershell -ExecutionPolicy Bypass -File scripts\servidor\instalar_servico_monitor.ps1
```

O monitor (avisos no grupo **HMPCF Avisos** do Telegram: sistema ou banco fora
do ar, backup atrasado e um "bom dia" às 07:30) precisa antes do arquivo
`C:\HMPCF\telegram.env`, fora do git:

```
TELEGRAM_TOKEN=<token do bot @hmpcf_avisos_bot; perdeu? /token no @BotFather>
TELEGRAM_CHAT=-5452174424
```

Teste: `backend\.venv\Scripts\python.exe scripts\servidor\monitor.py --teste`.
Se o "bom dia" das 07:30 não chegar, o servidor (ou o monitor) está desligado.

No **Google Drive para computador**: *Configurações → Meu computador →
Adicionar pasta* → `C:\HMPCF\backups_nuvem` → *Sincronizar com o Google Drive*.

Planilhas manuais da aba Entradas: a tabela `atendimentos_planilha` vem no
backup; as planilhas originais ficam em `C:\HMPCF\planilhas_manuais\` (guarde
uma cópia fora do servidor também).

## 6. Usuários e terminal da recepção

Os usuários (recepção, faturamento, TI) vêm no backup. Para o terminal fixo da
recepção entrar sozinho, `AUTO_LOGIN_LOCAL=true` no `backend\.env` (ver
`app/core/config.py`). Gerenciar usuários: `backend\scripts\gerenciar_usuarios.py`
ou a aba **Usuários** (TI).

## 7. Conferir

- [ ] `http://localhost:8001/health` → `{"status":"ok"}`
- [ ] Login funciona de outro PC em `http://192.168.1.29:8001`
- [ ] Aba **Painel** (TI): faixa do backup verde depois do primeiro backup
      (force um criando o arquivo `C:\HMPCF\backups\RODAR_AGORA`)
- [ ] `backend\.venv\Scripts\python -m alembic check` → nenhuma diferença
- [ ] Nos 2 notebooks, aba **BPA**: "Firebird OK" e migração/conferência
      falando com o servidor
- [ ] No dia seguinte: faixa do backup mostra "último … 23:0x"

## Atualizar o sistema (versão nova no GitHub)

No PowerShell como administrador:

```powershell
powershell -ExecutionPolicy Bypass -File C:\HMPCF-Automation-System\scripts\servidor\atualizar.ps1
```

O script baixa a versão nova, instala, monta as telas, reinicia (5 a 10 s fora
do ar, ninguém perde o login) e confere se o sistema respondeu. **Se algo der
errado, ele volta sozinho para a versão que estava rodando.** O resultado
aparece na tela e fica em `C:\HMPCF\atualizacoes.log`:

| Mensagem | O que fazer |
|---|---|
| `[OK] Atualizado` ou `Nada a fazer` | nada |
| `[PARADO]` | nada foi mexido; leia o motivo (arquivo alterado à mão, mudança no banco) |
| `[VOLTOU]` | o sistema está no ar na versão anterior; a nova ficou para depois |
| `[URGENTE]` | o sistema não subiu; ver `backend\nssm_backend.log` e os passos 4 e 5 acima |

Versão que muda o banco (pasta `backend/migrations`) o script não aplica: faça
o backup antes e rode `alembic upgrade head` à mão.

## Passagem para outro responsável

Quando o responsável atual (Fabio Gomes) deixar o hospital, o sistema continua
funcionando sozinho: os serviços sobem com o Windows e o backup roda todo dia.
Para alguém assumir, entregue os itens abaixo. Esta lista diz quem precisa ter
cada acesso, nunca as senhas; elas vão em papel lacrado ou num gerenciador de senhas.

| Acesso | Para quê | Entregue a |
|---|---|---|
| Usuário administrador do Windows do servidor | reiniciar serviços, instalar atualizações | [nome] |
| Senha do `postgres` (`backend\.env`) | manutenção do banco | [nome] |
| **Senha de criptografia do backup** | abrir qualquer backup | [nome] (e cópia no cofre) |
| Senha do `bpa_leitura` | reinstalar o BPA nos notebooks | [nome] |
| Conta Google do Drive dos backups | conferir a cópia na nuvem | [nome] |
| Grupo **HMPCF Avisos** no Telegram (e dono do bot `@hmpcf_avisos_bot`) | receber os avisos do monitor | adicionar ao grupo; passar o bot pelo @BotFather |
| Conta **TI** no sistema | Painel, Auditoria, Usuários | criar uma conta TI para o novo responsável; depois desativar a do anterior |

- [ ] Todos os acessos da tabela entregues e testados por quem assume
- [ ] Backup do dia anterior conferido no Painel (faixa verde) e no Drive
- [ ] Um backup aberto de teste com `decrypt_backup.ps1`, para provar que a senha confere
- [ ] Quem assume sabe reiniciar o `HMPCF-Backend-Svc` (ver *StopPending* no README)
- [ ] Quem assume sabe atualizar com `atualizar.ps1` (seção acima)
- [ ] Este guia e o README lidos por quem assume

O código fica em `C:\HMPCF-Automation-System`, com o histórico completo; ele
basta para manter e reinstalar o sistema, mesmo sem acesso ao GitHub. O uso
pelo hospital é autorizado pelo autor (ver `LICENSE`). Depois da saída dele,
suporte, manutenção e novas funções só mediante contratação específica.

## Se for só restaurar o banco (o servidor continua de pé)

Pare o `HMPCF-Backend-Svc`, recrie o banco (passo 3), rode
`alembic upgrade head` e suba o serviço de novo.
