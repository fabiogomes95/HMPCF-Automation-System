# Atalho da área de trabalho — BPA HMPCF

Este documento explica como criar, em **qualquer PC** que já tenha o sistema
`bpa/` funcionando (venv configurado, `.env` certo, Firebird local com
`BPAMAG.GDB`), um atalho na área de trabalho igual ao usado em produção:
clica, não aparece nenhuma janela de console, o navegador abre sozinho com
o sistema já rodando em `http://localhost:8503`.

---

## Arquivos envolvidos (já estão no repositório, não precisa criar)

- `bpa/iniciar_bpa_silencioso.bat` — inicia o Flask (se ainda não estiver
  rodando na porta 8503) e depois abre o navegador.
- `bpa/start_bpa.vbs` — roda o `.bat` acima **escondido** (sem janela preta
  de console aparecendo).
- `legado/assets/robo-icon.ico` — ícone do robozinho, reaproveitado do
  atalho antigo do Painel de Gestão.

Se algum desses arquivos não existir depois do `git pull`, confira se está
na versão mais recente do repositório.

---

## Passo a passo — criar o atalho

### Opção rápida (PowerShell)

Abra o PowerShell **na pasta onde o repositório está clonado** e rode:

```powershell
$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut("$env:USERPROFILE\Desktop\Painel HMPCF.lnk")
$lnk.TargetPath       = "$PWD\bpa\start_bpa.vbs"
$lnk.WorkingDirectory = "$PWD\bpa"
$lnk.IconLocation     = "$PWD\legado\assets\robo-icon.ico,0"
$lnk.Description      = "BPA HMPCF - Digitacao, Enfermeiros e Migracao"
$lnk.Save()
```

> Ajuste `$PWD` se não estiver rodando o comando de dentro da pasta do
> repositório — substitua pelo caminho completo, ex:
> `C:\HMPCF-Automation-System\bpa\start_bpa.vbs`.

### Opção manual (Explorer)

1. Clique com o botão direito na área de trabalho → **Novo → Atalho**.
2. Em "Digite o local do item", cole o caminho completo do
   `start_bpa.vbs`, por exemplo:
   ```
   C:\HMPCF-Automation-System\bpa\start_bpa.vbs
   ```
3. Nomeie o atalho como **Painel HMPCF** e finalize.
4. Clique com o botão direito no atalho criado → **Propriedades**.
5. Em **Iniciar em**, coloque a pasta `bpa\` (ex:
   `C:\HMPCF-Automation-System\bpa`).
6. Clique em **Alterar Ícone...**, navegue até
   `legado\assets\robo-icon.ico` e selecione.
7. **OK** para salvar.

---

## Testar

1. Feche qualquer instância do BPA que já esteja rodando (não é obrigatório,
   o `.bat` detecta se a porta 8503 já está em uso e só abre o navegador
   nesse caso, sem duplicar o processo).
2. Dê duplo clique no atalho **Painel HMPCF**.
3. Não deve aparecer nenhuma janela preta de console.
4. Em alguns segundos, o navegador abre sozinho em
   `http://localhost:8503` com o sistema já carregado.

Se o navegador abrir mostrando erro de conexão, é porque o servidor ainda
estava subindo (carregar os pacientes do Firebird pode levar alguns
segundos) — só dar F5 depois de uns 5 segundos.

---

## Solução de problemas

- **Log de inicialização**: `bpa\start_bpa.log` — mostra se o script achou
  a porta já em uso ou se iniciou o servidor agora.
- **Nada abre / navegador não conecta**: confira se
  `dashboard\.venv\Scripts\pythonw.exe` existe (ambiente virtual precisa
  estar montado — ver `docs/INSTALACAO_BPA_MIGRACAO.md`).
- **Ícone não aparece / aparece em branco**: confirme que o caminho do
  `legado\assets\robo-icon.ico` está correto e que a pasta `legado/` não
  foi removida (o ícone é reaproveitado de lá, não foi duplicado).
