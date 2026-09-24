# BPA local — notebooks do faturamento

Programa que roda em cada notebook do BPA, ao lado do Firebird e do BPA
Magnético (`C:\BPA`). As telas ficam no sistema do hospital
(`http://192.168.1.29:8001`, aba **BPA**); quem faz o trabalho no Firebird é
este programa, em `http://localhost:8503` (só aceita chamadas do sistema).

## Instalar / atualizar

No PowerShell, na pasta do sistema (não precisa ser administrador):

```powershell
cd C:\HMPCF-Automation-System
git pull
powershell -ExecutionPolicy Bypass -File bpa\instalar.ps1
```

O `instalar.ps1` (rodar de novo = atualizar):

1. cria/atualiza o Python do BPA em `bpa\.venv`;
2. confere o `bpa\.env` (Firebird, `bpa_leitura`, pasta dos lotes — modelo em
   `bpa\.env.example`) e mostra a **pasta dos lotes** (nos notebooks:
   `C:\BPA\bpa_lotes`);
3. registra a tarefa `HMPCF-BPA`, que liga o BPA sozinho ao entrar no Windows,
   e reinicia o BPA;
4. cria o atalho **HMPCF - BPA** na área de trabalho (abre o sistema no
   Chrome, ícone do robô `bpa\robo-icon.ico`) e apaga o atalho antigo do BPA
   Flask.

Depois de um `git pull` que mexe no BPA (leitura de planilha, geração,
Firebird), rode o `instalar.ps1` de novo pra reiniciar com o código novo.
Mudança só nas telas não precisa: basta F5.

## Onde fica cada coisa

| O quê | Onde |
|---|---|
| Lotes de digitação (`DD-MM-AAAA.txt`) e arquivos gerados | `BPA_LOTES_DIR` do `bpa\.env` (padrão `C:\BPA\bpa_lotes`) |
| Configuração deste notebook | `bpa\.env` (fora do git) |
| Log do BPA | `bpa\bpa_local.log` |
| Cópia dos lotes no servidor | tabela `bpa_lotes_backup` (restaurar: `ferramentas\restaurar_lotes.py`) |

A barra do topo da aba BPA mostra "lotes em …" — confira se é a pasta certa.

## Problemas

- **"BPA deste notebook não está respondendo"**: espere 1 minuto (ele carrega
  os pacientes do Firebird ao ligar) e clique em *Tentar de novo*. Se
  continuar, rode `bpa\iniciar.bat` (abre com janela, mostra o erro na tela).
- **Pasta dos lotes errada**: ajuste `BPA_LOTES_DIR` no `bpa\.env` e rode o
  `instalar.ps1`.

O BPA antigo em Flask (`app.py`, `start_bpa.vbs`…) está em
`legado/bpa_antigo/`.
