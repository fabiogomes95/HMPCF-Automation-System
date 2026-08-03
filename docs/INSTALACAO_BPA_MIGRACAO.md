# Instalação do BPA (Flask) + Migração PostgreSQL → Firebird — nova máquina

**Para quem é este guia:** uma instância do Claude Code rodando numa máquina
local diferente, que precisa deixar o app `bpa/` funcionando e executar a
mesma migração de pacientes (Postgres → Firebird/CADCNS) já validada em
outra máquina.

**Contexto:** o app `bpa/` (Flask, porta padrão 8503) faz duas coisas: (1)
digitação de BPA usando um Firebird **local** desta máquina (`C:\BPA\BPAMAG.GDB`),
e (2) migra pacientes cadastrados na recepção digital (PostgreSQL, servidor
remoto) para esse mesmo Firebird local, preenchendo CPF em cadastros antigos
que só tinham CNS. Cada máquina tem sua **própria** cópia do Firebird/CADCNS —
não é um banco compartilhado entre máquinas.

---

## 0. Antes de tudo: isso é uma decisão do usuário, não só um script

Confira se esta máquina **já tem** Firebird instalado com `C:\BPA\BPAMAG.GDB`:

```powershell
Get-Service | Where-Object { $_.DisplayName -match "firebird" }
Test-Path C:\BPA\BPAMAG.GDB
```

- **Se SIM** (serviço rodando e arquivo existe): pule para o passo 1. Você só
  vai instalar o app `bpa/` por cima do que já existe.
- **Se NÃO**: **pare e avise o usuário antes de continuar.** `BPAMAG.GDB` é o
  banco de cadastro de pacientes (CADCNS) usado pelo BPA Magnético — é dado
  de produção do hospital, não algo pra copiar ou recriar sem confirmação
  explícita de onde deve vir a cópia. Este guia não cobre instalar o
  Firebird do zero nem provisionar um `BPAMAG.GDB` novo/copiado.

---

## 1. Clonar (ou atualizar) o repositório

```powershell
git clone https://github.com/fabiogomes95/HMPCF-Automation-System.git C:\HMPCF-Automation-System
cd C:\HMPCF-Automation-System
```

Se a pasta já existir, só `git pull origin main` dentro dela.

---

## 2. Ambiente Python (venv compartilhado com o dashboard)

O `bpa/iniciar.bat` roda com o Python do `dashboard/.venv` (não tem venv
próprio):

```powershell
cd C:\HMPCF-Automation-System\dashboard
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Isso instala `flask`, `psycopg2-binary`, `firebirdsql`, `python-dotenv`,
entre outros — confira `dashboard/requirements.txt` se algo faltar.

---

## 3. Configurar `dashboard/.env` (credenciais do Firebird local)

Esse arquivo é `.gitignore`d — não vem do clone, precisa criar/editar à mão.
Se já existir (porque a máquina já rodava o BPA antigo), só confira os
valores:

```env
FIREBIRD_PATH=C:\BPA\BPAMAG.GDB
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=<peça ao usuário — não é a mesma senha do Postgres>
BPA_LOTES_DIR=<pasta local para os lotes .txt>
```

---

## 4. Configurar `bpa/.env` (conexão com o Postgres remoto)

Criar `bpa/.env` (também `.gitignore`d):

```env
BPA_LOTES_DIR=C:\BPA\bpa_lotes
BPA_SAIDA_DIR=C:\BPA
POSTGRES_HOST=<ver nota abaixo — NÃO usar o hostname direto>
POSTGRES_PORT=5432
POSTGRES_DB=hmpcf
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<peça ao usuário — é a mesma senha usada em backend/.env do servidor remoto>
```

### ⚠️ `POSTGRES_HOST`: use o IP, não o hostname "Desktop-9c4s1co"

Já tivemos esse bug de verdade numa outra máquina: em PCs com várias
interfaces de rede (Wi-Fi, Bluetooth, adaptadores virtuais/VPN), o hostname
`Desktop-9c4s1co` pode resolver para um endereço **IPv6 link-local**
(`fe80::...`) ambíguo — o Windows escolhe a interface errada e a conexão
quebra no meio do handshake com psycopg2 dando exatamente este erro:

```
OperationalError: connection to server at "Desktop-9c4s1co" (fe80::...), port 5432 failed:
server closed the connection unexpectedly
This probably means the server terminated abnormally
before or while processing the request.
```

**Se esse erro aparecer, é isso.** A correção é descobrir o IPv4 real do
servidor e usar ele direto em `POSTGRES_HOST`. Da última vez era
`192.168.1.13` (rede do hospital, 2026-07) — **confirme, pode ter mudado**.

Se você tiver WinRM configurado com o servidor remoto (ver
`docs/CONFIGURAR_WINRM_INSTRUCOES.txt`), dá pra confirmar assim:

```powershell
Invoke-Command -ComputerName Desktop-9c4s1co -ScriptBlock {
    Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
}
```

Sem WinRM, peça o IP ao usuário (`ipconfig` no próprio servidor remoto).

---

### ⚠️ Erro `'utf-8' codec can't decode byte 0xe7 ... invalid continuation byte`

Outro bug real (2026-08-03): a aba Migração dava esse erro ao tentar conectar
no Postgres. **Não é um problema de encoding em si** — é a mensagem real do
libpq vindo em português (Latin1, com acento) e o psycopg2 tentando decodificar
como UTF-8 antes de repassar a exceção, o que quebra e esconde o erro
verdadeiro por trás de um `UnicodeDecodeError` ilegível.

`_pg_connect()` em `bpa/app.py` já foi corrigida para capturar esse
`UnicodeDecodeError` e decodificar a mensagem como Latin1 antes de propagar —
então, se isso acontecer de novo (já com essa correção no código), o erro que
aparece na tela já vai vir legível, tipo:

```
FATAL:  autenticação do tipo senha falhou para o usuário "postgres"
```

Se ainda assim o erro vier ilegível (código sem a correção, ou erro em outro
lugar que não passa por `_pg_connect`), rode isto pra ver a mensagem real
antes do psycopg2 quebrar o decode:

```python
import psycopg2
try:
    psycopg2.connect(host="...", port=5432, dbname="hmpcf", user="postgres",
                      password="...", connect_timeout=5,
                      options="-c client_encoding=LATIN1")
except UnicodeDecodeError as e:
    print(e.object.decode("latin1", errors="replace"))
```

No caso real, a mensagem decodificada foi "autenticação do tipo senha falhou
para o usuário postgres" — ou seja, **senha errada** em `POSTGRES_PASSWORD`
(`bpa/.env`), nada de rede/firewall. A correção foi simplesmente atualizar a
senha no `.env` pra bater com a senha atual do usuário `postgres` no servidor
(peça ao usuário, não adivinhe/reuse uma senha antiga).

---

## 5. Testar as duas conexões antes de subir o app

**Postgres** (não hardcode a senha no comando — leia do `.env` em runtime):

```python
# script temporário, ex: teste_pg.py — lê bpa/.env, não imprime a senha
import psycopg2
env = {}
with open(r"C:\HMPCF-Automation-System\bpa\.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

conn = psycopg2.connect(
    host=env["POSTGRES_HOST"], port=int(env.get("POSTGRES_PORT", 5432)),
    dbname=env.get("POSTGRES_DB", "hmpcf"), user=env.get("POSTGRES_USER", "postgres"),
    password=env.get("POSTGRES_PASSWORD", ""), connect_timeout=5,
    options="-c client_encoding=LATIN1",
)
print("OK:", conn.cursor().execute("SELECT version()") or "conectado")
conn.close()
```

**Firebird local** — de dentro de `dashboard/`, com o venv:

```python
import sys; sys.path.insert(0, r"C:\HMPCF-Automation-System\dashboard")
import bpa_gerador as bpa
con = bpa.conectar()
print("OK, CADCNS tem", con.cursor().execute("SELECT COUNT(*) FROM CADCNS") or "?", "registros")
```

Se o Firebird der erro de UDF (`Use of UDF library ... not allowed`), evite
funções como `TRIM()` nas queries — não é permitido pela configuração do
servidor; use `.strip()` no Python depois de buscar os dados.

---

## 6. Subir o app

```powershell
cd C:\HMPCF-Automation-System\bpa
..\dashboard\.venv\Scripts\python.exe app.py
```

Acesse `http://localhost:8503`. Antes de testar a aba **Migração**, confirme
que só tem **um** processo rodando (evita lentidão por concorrência no
Firebird):

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "app.py" }
```

Se aparecer mais de um, mate os extras (`Stop-Process -Id <pid> -Force`) e
deixe só um antes de testar.

---

## 7. Rodar a migração

Na aba **Migração**: escolha a competência, clique em **🔍 Ver resumo**.

- Deve responder em **poucos segundos**, mesmo em meses com milhares de
  pacientes — se demorar minutos, é sinal de processo duplicado do app.py
  brigando pelo Firebird (ver passo 6) ou de algo errado na query.
- O resumo mostra 4 números: **Novos** (não existiam), **Só falta CPF**
  (já tinham cadastro por CNS, vão ganhar o CPF via UPDATE), **Já com CPF**
  (nada a fazer), **CPF inválido** (pulado, não migra).
- Confira os números antes de clicar em **▶ Migrar**.

### O que essa migração faz (resumo do comportamento)

- Só migra pacientes com CPF **válido de verdade** (algoritmo oficial com
  dígitos verificadores — não só contagem de 11 dígitos).
- CNS **não é mais obrigatório**, mas continua sendo gravado quando existe
  (ainda é usado na digitação manual, quem digita costuma buscar por CNS).
- Paciente que já existe no Firebird pelo CNS mas está sem CPF: o app faz
  `UPDATE CADCNS SET NUM_CPF = ...` **só nesse campo**, sem tocar no resto
  do cadastro.
- Paciente que não existe de jeito nenhum: insere novo, com
  `ID_CADCNS = MAX(ID_CADCNS) + 1` calculado uma vez e incrementado em
  memória (evita colisão de chave primária).

---

*Gerado a partir de uma sessão real de configuração/depuração em outra
máquina (2026-07-01). Se algo aqui não bater com o que você encontrar,
confie no que você observar na máquina atual — este documento descreve o
que era verdade na outra época/máquina, não uma garantia.*
