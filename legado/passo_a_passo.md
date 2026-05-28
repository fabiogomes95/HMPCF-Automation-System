# Passo a Passo — Setup do Sistema HMPCF em outro PC

## 1. Clonar o repositório

```cmd
cd C:\
git clone https://github.com/fabiogomes95/HMPCF-Automation-System.git
cd HMPCF-Automation-System
```

## 2. Instalar Python 3.14 (64-bit)

Baixar do site oficial: https://www.python.org/downloads/

**IMPORTANTE:** Marcar "Add Python to PATH" durante a instalação.

Verificar:
```cmd
python --version
```
Tem que mostrar: `Python 3.14.x`

## 3. Verificar Firebird 1.5

O banco legado `BPAMAG.GDB` fica em `C:\BPA\`. O Firebird 1.5 precisa estar
instado e rodando como servidor:

```cmd
sc query FirebirdServerDefaultInstance
```
Se não estiver rodando:
```cmd
net start FirebirdServerDefaultInstance
```

## 4. Instalar dependências

```cmd
cd C:\HMPCF-Automation-System
pip install -r requirements.txt
```

Se der erro de permissão, use:
```cmd
pip install --user -r requirements.txt
```

## 5. Configurar .env

```cmd
copy .env.example .env
```

Editar `.env` com bloco de notas e ajustar se necessário os caminhos:
- `FIREBIRD_PATH` — caminho do `BPAMAG.GDB`
- `DB_SQLITE` — caminho do `hospital.db`

Os valores padrão já funcionam para o hospital.

## 6. Verificar conexão com Firebird

```cmd
python -c "import firebirdsql; con = firebirdsql.connect(host='localhost', database=r'C:\BPA\BPAMAG.GDB', user='SYSDBA', password='masterkey', charset='WIN1252'); cur = con.cursor(); cur.execute('SELECT COUNT(*) FROM CADCNS'); print('Conectado! Total:', cur.fetchone()[0]); con.close()"
```

## 7. Rodar o reparo do Firebird (corrigir registros antigos)

```cmd
cd C:\HMPCF-Automation-System\AUTOMACAO
python REPARAR_FIREBIRD.py
```

Isso corrige:
- IDs nulos (ID_CADCNS)
- Código da rua zerado (CO_LOGRAD)
- Endereços vazios (LOGPCN, NUMPCN, BAIRRO_PCNTE)
- Sexo inválido (SEXO)
- Raça vazia (RACA)

## 8. Migrar pacientes do SQLite para o Firebird (se necessário)

```cmd
cd C:\HMPCF-Automation-System\AUTOMACAO
python MIGRAR_PACIENTES.py
```

Isso lê o `hospital.db` e insere no `CADCNS` do Firebird.

## 9. Iniciar o sistema

```cmd
cd C:\HMPCF-Automation-System
python main.py
```

Isso inicia:
- Painel de Gestão → http://localhost:8001
- Recepção → http://localhost:8000

## 10. Usar o Robô RPA (digitação automática BPA)

1. Abrir o painel: http://localhost:8001
2. Ir na aba "Robô"
3. Selecionar o arquivo de produção
4. Clicar "Iniciar Automação BPA"

**Antes de iniciar o robô:**
- Manter o sistema BPA/SUS aberto e visível na tela
- Não mexer no mouse/teclado durante a execução
- O robô impede o Windows de suspender automaticamente

Para interromper: pressionar `ESC` ou levar o mouse para o canto da tela.

---

## Resolução de problemas

### Erro "fbclient.dll" / WinError 193

O Python 64-bit não carrega DLL 32-bit do Firebird 1.5.
O sistema usa `firebirdsql` (puro Python), que não precisa da DLL.
**Não instalar fdb.**

### Robô para sozinho após inatividade

O script `executor_rpa.py` já inclui a função `manter_acordado()` que
chama `SetThreadExecutionState` para evitar suspensão. Se ainda parar:
- Verificar se o Windows Update não está reiniciando
- Verificar configurações de energia: **Desligar disco rígido: Nunca**

### Banco corrompido / "Could not convert" no BPA

Rodar o reparo:
```cmd
cd C:\HMPCF-Automation-System\AUTOMACAO
python REPARAR_FIREBIRD.py
```

### Dependências não instalam

Tentar com Python mais recente ou instalar manualmente:
```cmd
pip install pyautogui keyboard firebirdsql pandas openpyxl xlsxwriter
pip install fpdf2 eel pyinstaller
```
