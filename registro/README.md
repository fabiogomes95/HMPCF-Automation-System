# Registro de Sessão — HMPCF Automation System

> Arquivo criado para manter continuidade entre sessões.
> Use este arquivo como referência quando retomar o trabalho.

---

## Sessão 1 — 2026-05-15

### Problema resolvido: Build .exe falhando no GitHub Actions
**Erro:** `pyinstaller recepcao.spec --onefile` — `--onefile` é flag de makespec, não aceita quando .spec é passado.
**Solução:** Movido `onefile=True` para dentro dos .spec files (`recepcao.spec`, `painel.spec`). Removido `--onefile` do `build.yml`.

### Renomeação de arquivos
- `ideias.md` → `backlog.md` (pendências e ideias futuras)
- Criado `CHANGELOG.md` (histórico de alterações)

### Organização do código
**Arquivos alterados para usar `config.py`:**
- `app_painel.py` — Firebird user/password/path
- `planilha_nuvem.py` — Google Sheet ID, escopos, caminho SQLite
- `corrigir_data.py` — Firebird credenciais
- `integracao/sincronizar_firebird.py` — Firebird credenciais
- `integracao/duplicatas_gdb.py` — Firebird credenciais
- `integracao/corrigir_nulls.py` — Firebird credenciais
- `integracao/exportar_bpa.py` — CNS_PROFISSIONAL, CBO, etc.
- `integracao/converter_csv.py` — CNS_PROFISSIONAL, CBO, etc.
- `scripts/sinc_nome.py` — Firebird credenciais

**Arquivos criados:**
- `config.py` — lê `.env` ou usa defaults (sem `.env` o sistema funciona igual)
- `.env.example` — template comentado
- `pyproject.toml` — estrutura de pacote Python
- `__init__.py` com docstrings em `automacao/`, `analise/`, `integracao/`, `scripts/`

**Diretórios renomeados:**
- `archive/` → `scripts/` (sem quebra de imports)

**Removido:**
- `.spec` files (`painel.spec`, `recepcao.spec`, `main.spec`)
- `.github/workflows/build.yml`
- `.exe` da release `v1.1.0` (3 arquivos: HMPCF.exe, HMPCF_Painel.exe, HMPCF_Recepcao.exe)

---

## Sessão 2 — 2026-05-16

### Startup scripts para Windows 11
**Criados para iniciar cada servidor separadamente:**

| Arquivo | Função |
|---|---|
| `iniciar_painel.bat` | Inicia Painel (porta 8001) com pythonw |
| `iniciar_recepcao.bat` | Inicia Recepção (porta 8000) com pythonw |
| `start_painel.vbs` | Executa `iniciar_painel.bat` invisível |
| `start_recepcao.vbs` | Executa `iniciar_recepcao.bat` invisível |

**Removidos:** `iniciar.bat`, `start.vbs` (substituídos pelos específicos)

**Movido:** `corrigir_data.py` → `scripts/`

### Instruções para criar atalhos no Windows 11
1. Botão direito na Área de Trabalho → Novo → Atalho
2. **Painel:** `wscript.exe "C:\caminho\HMPCF-Automation-System\start_painel.vbs"`
3. **Recepção:** `wscript.exe "C:\caminho\HMPCF-Automation-System\start_recepcao.vbs"`

### Como usar o sistema sem .exe
- Dar `git pull` em cada máquina do hospital
- Cada máquina precisa ter Python 3.10+ e `pip install -r requirements.txt`
- O `hospital.db` fica na raiz do projeto (cada máquina tem o seu)
- `credentials.json` precisa estar na raiz (Google Sheets)

### Arquitetura atual
```
HMPCF-Automation-System/
├── app_painel.py          # Servidor web Painel (porta 8001)
├── app_recepcao.py        # Servidor web Recepção (porta 8000)
├── config.py              # Config centralizada (Firebird, Google, BPA)
├── .env.example           # Template de configuração (opcional)
├── automacao/             # RPA, CPF/SUS, digitação
├── integracao/            # Firebird sync, BPA export, CSV import
├── analise/               # BI: dashboards, relatórios, auditoria
├── scripts/               # Ferramentas DBA: faxina, fusão, validação
├── web_painel/            # Frontend do Painel (HTML/JS)
├── web_recepcao/          # Frontend da Recepção (HTML/JS)
├── hospital.db            # SQLite local (pacientes + atendimentos)
├── credentials.json       # Chave Google Cloud (não versionada)
├── requirements.txt       # Dependências Python
└── pyproject.toml         # Estrutura de pacote
```

### Portas
- **8000** — Recepção (cadastro de pacientes)
- **8001** — Painel de Gestão (BI, RPA, integração Firebird)

### Banco de dados Firebird
- **Caminho:** `C:/BPA/BPAMAG.GDB`
- **Usuário:** `SYSDBA`
- **Senha:** `masterkey`
- **Host:** `localhost`
- Tudo configurável via `.env` se necessário

### Google Sheets (Gari da Nuvem)
- **credentials.json** — serviço Google Cloud (já na pasta)
- **Sheet ID:** `1xw_x-bYlHCHzMe39g1mJKPFAD_IcXA8BB0uRfmmuR90`
- Sincroniza atendimentos da recepção em tempo real
