# Instalação do Sistema HMPCF — PC da Recepção

**Para quem é este guia:** quem vai instalar o sistema em um PC do hospital, mesmo sem conhecimento técnico avançado.

**O que vamos instalar:** o sistema novo (FastAPI + PostgreSQL + React), mantendo o banco de dados do sistema legado intacto para importar o histórico de pacientes.

**Tempo estimado:** 30–60 minutos (dependendo da internet).

---

## Antes de começar — o que você vai precisar

- Um PC com **Windows 10 ou 11 de 64 bits**
- **Acesso de Administrador** na máquina
- **Internet** durante a instalação (para baixar os programas)
- O arquivo **`hospital.db`** — é o banco de dados do sistema legado com todos os pacientes. Ele será usado **apenas para importar o histórico** (uma única vez). Depois disso, o sistema novo não toca mais nele.

---

## Passo 1 — Abrir o PowerShell como Administrador

Toda a instalação roda no PowerShell. Faça isso da forma certa:

1. Pressione a tecla **Windows** no teclado
2. Digite: `powershell`
3. Clique com o botão **direito** em "Windows PowerShell"
4. Clique em **"Executar como administrador"**
5. Vai aparecer uma caixa perguntando se permite — clique em **Sim**

Uma janela azul vai abrir. Deixe ela aberta durante toda a instalação.

> **Por que precisa de administrador?** Para instalar o banco de dados (PostgreSQL) e registrar o sistema para iniciar automaticamente com o Windows.

---

## Passo 2 — Verificar se o winget está disponível

O `winget` é o instalador de programas do Windows. Cole este comando e pressione Enter:

```powershell
winget --version
```

**Resultado esperado:**
```
v1.x.x
```

**Se aparecer erro** ("winget não reconhecido"):
- Abra a **Microsoft Store**
- Pesquise por **"App Installer"**
- Clique em **Atualizar** ou **Instalar**
- Feche e reabra o PowerShell como Administrador e tente de novo

---

## Passo 3 — Clonar o repositório (baixar os arquivos do sistema)

Cole estes dois comandos e pressione Enter após cada um:

```powershell
New-Item -ItemType Directory -Force -Path C:\HMPCF | Out-Null
git clone https://github.com/fabiogomes95/HMPCF-Automation-System.git C:\HMPCF
```

> Se o `git` não estiver instalado, não se preocupe — o script de instalação do Passo 5 vai instalar automaticamente. Mas se aparecer erro aqui, continue mesmo assim.

**Se o git estiver instalado**, você verá algo como:
```
Cloning into 'C:\HMPCF'...
remote: Enumerating objects: ...
Receiving objects: 100% ...
```

---

## Passo 4 — Copiar o `hospital.db` para importar o histórico

O `hospital.db` é o banco de dados do sistema antigo. O script de instalação vai **ler ele uma única vez** para importar todos os pacientes e atendimentos para o banco novo (PostgreSQL). Depois da importação, o arquivo fica parado sem ser usado.

> Pense nisso como digitalizar fichas de papel: você usa as fichas para digitar tudo no computador, depois guarda as fichas numa gaveta.

**Localize o `hospital.db`** (pode estar em um pen drive, em `C:\HMPCF-Automation-System\legado\`, ou em outra pasta) e **copie ele para:**

```
C:\HMPCF\legado\hospital.db
```

Para confirmar que está no lugar certo, cole este comando:

```powershell
Test-Path C:\HMPCF\legado\hospital.db
```

**Resultado esperado:**
```
True
```

Se aparecer `False`, o arquivo ainda não está no lugar certo. Procure o `hospital.db` e copie para o caminho indicado antes de continuar.

---

## Passo 5 — Ajustar a senha do banco de dados

O script de instalação vai criar o banco com uma senha. Antes de rodar, você pode definir a senha que quiser.

Abra o arquivo no Bloco de Notas:

```powershell
notepad C:\HMPCF\DEPLOY_HMPCF_REMOTO.ps1
```

Não precisa editar senha no arquivo — o script pede a senha do PostgreSQL
interativamente (`Read-Host -AsSecureString`) quando você rodar, e ela nunca
fica salva em texto puro no script nem no Git.

> **Anote a senha que você digitar!** Você vai precisar dela se precisar fazer
> manutenção no banco depois.

---

## Passo 6 — Rodar o script de instalação

Este é o passo principal. Um único comando vai fazer tudo automaticamente:

- Instalar o PostgreSQL (banco de dados)
- Instalar Python, Git e Node.js (se não tiver)
- Configurar o banco de dados
- Importar todos os pacientes e atendimentos do sistema legado
- Fazer o build do site (React)
- Registrar o sistema para iniciar automaticamente com o Windows
- Configurar backup diário automático
- Abrir a porta no firewall
- Criar atalho na área de trabalho

Cole este comando e pressione Enter:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
C:\HMPCF\DEPLOY_HMPCF_REMOTO.ps1
```

**O que vai aparecer na tela:**

Você vai ver mensagens coloridas. **Verde = OK**, **Amarelo = aviso (não é erro)**, **Vermelho = problema**.

```
==> Verificando ambiente Windows...
    [OK] Sistema 64-bit OK

==> Instalando PostgreSQL 16...
    Baixando instalador PostgreSQL 16 (~300 MB)...   ← pode demorar
    [OK] PostgreSQL 16 instalado e rodando

==> Instalando Python 3.11...
==> Instalando Git...
==> Instalando Node.js LTS...

==> Clonando / atualizando repositorio...
    [OK] Encontrado: C:\HMPCF\backend\app\main.py
    [OK] Encontrado: C:\HMPCF\legado\hospital.db

==> Criando tabelas e migrando dados (SQLite -> PostgreSQL)...
    [OK] Migracao concluida
    [OK] Pacientes migrados   : 29242
    [OK] Atendimentos migrados: 11687

==> Build do frontend...
    [OK] Frontend buildado

==> Registrando servico HMPCF-Backend...
    [OK] Servico HMPCF-Backend rodando

==> Configurando backup automatico...
    [OK] Backup agendado para 23:00

================================================================
  DEPLOY HMPCF CONCLUIDO
================================================================

  Acesso:
    Local:  http://localhost:8001
    Rede:   http://192.168.x.x:8001   ← anote este IP!
```

> **Atenção:** A instalação do PostgreSQL baixa cerca de 300 MB e pode demorar 10–15 minutos dependendo da internet. Não feche o PowerShell enquanto estiver rodando.

---

## Passo 7 — Verificar que o sistema está funcionando

Após o script terminar, abra o navegador e acesse:

```
http://localhost:8001
```

Você deve ver a tela de Recepção do HMPCF.

**Teste básico:**
- [ ] A tela de Recepção abre
- [ ] Busca por CPF de um paciente existente traz os dados
- [ ] Aba **Histórico** mostra atendimentos antigos

**Health check** (confirma que o backend está rodando):

```powershell
Invoke-WebRequest http://localhost:8001/health | Select-Object -Expand Content
```

Resultado esperado:
```json
{"status":"ok","app":"HMPCF","env":"production"}
```

---

## Passo 8 — Verificar a importação dos dados

Confirme que os pacientes e atendimentos foram importados corretamente:

```powershell
$env:PGPASSWORD = Read-Host -Prompt "Senha do PostgreSQL" -AsSecureString |
    ConvertFrom-SecureString -AsPlainText
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -d hmpcf -c "SELECT COUNT(*) AS pacientes FROM pacientes;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -d hmpcf -c "SELECT COUNT(*) AS atendimentos FROM recepcao_atendimentos;"
```

> Digite a senha que você definiu no Passo 5 quando for solicitado.

Resultado esperado (os números podem variar):
```
 pacientes
-----------
     29242

 atendimentos
--------------
        11687
```

---

## Passo 9 — Segunda máquina (estação cliente)

Na segunda máquina, **não precisa instalar nada**. Só precisa de um navegador.

1. Anote o IP que apareceu no final da instalação (linha `Rede: http://192.168.x.x:8001`)
2. Na segunda máquina, abra o Chrome ou Edge e acesse:
   ```
   http://192.168.x.x:8001
   ```
   (substituindo pelo IP real da máquina servidor)
3. Para criar um atalho fácil na área de trabalho:
   - No Chrome/Edge: clique nos três pontinhos → Mais ferramentas → Criar atalho → marque "Abrir como janela"

> **Dica:** Peça ao técnico de rede para fixar o IP da máquina servidor no roteador. Assim o IP nunca muda e o atalho sempre funciona.

---

## Sobre o sistema legado

O sistema legado continua existindo em `C:\HMPCF\legado\` e o `hospital.db` está intacto — nada foi apagado ou modificado. A importação apenas **leu** o banco legado.

**O legado e o sistema novo não podem rodar ao mesmo tempo** porque os dois usam a mesma porta (8001). Se precisar abrir o sistema legado em emergência:

```powershell
# 1. Parar o sistema novo
net stop HMPCF-Backend

# 2. Abrir o sistema legado manualmente
cd C:\HMPCF\legado
python app_painel.py

# 3. Quando terminar, voltar o sistema novo
net start HMPCF-Backend
```

---

## Comandos do dia a dia

```powershell
# Ver se o sistema está rodando
Get-Service HMPCF-Backend, postgresql-x64-16

# Reiniciar o backend (após atualização)
net stop HMPCF-Backend; net start HMPCF-Backend

# Atualizar o sistema (baixar nova versão)
cd C:\HMPCF
git pull origin main
cd frontend; npm run build; cd ..
net stop HMPCF-Backend; net start HMPCF-Backend

# Ver logs (para investigar um problema)
Get-Content C:\HMPCF\logs\backend.log -Tail 50

# Fazer backup agora
C:\HMPCF\scripts\backup_postgres.bat
```

---

## Problemas comuns

| Problema | O que fazer |
|----------|-------------|
| "winget não reconhecido" | Instale o App Installer pela Microsoft Store |
| Script para com texto vermelho | Leia a mensagem. Na maioria das vezes é falta de internet ou senha errada |
| `Test-Path` retorna `False` para o hospital.db | O arquivo não está no lugar certo. Copie para `C:\HMPCF\legado\hospital.db` |
| Sistema abre mas não acha pacientes | A importação pode ter falhado. Veja `C:\HMPCF\scripts\migration.log` |
| Segunda máquina não acessa | Confirme o IP do servidor com `ipconfig` e verifique se o firewall foi liberado |
| Após reiniciar o PC o sistema não sobe | Execute `net start HMPCF-Backend` no PowerShell como Administrador |

---

*Documento atualizado em 2026-06-15.*
