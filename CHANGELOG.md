# Changelog

## [2026-05-15]

### Added
- **`config.py`** — Configuração centralizada lendo de `.env` (Firebird, Google Sheets, BPA).
- **`.env.example`** — Template para configuração local (não contém senhas reais).
- **`pyproject.toml`** — Estrutura de pacote Python (pip install -e .).
- **`__init__.py`** com docstrings nos pacotes `automacao/`, `analise/`, `integracao/`, `scripts/`.

### Changed
- **`archive/` → `scripts/`** — Renomeado diretório e atualizadas todas as referências nos docstrings.
- **`app_painel.py`**, **`corrigir_data.py`**, **`integracao/banco_de_dados_hospital_bpa.py`**, **`integracao/duplicatas_gdb.py`**, **`integracao/nacionalidade_gdb.py`**, **`scripts/cpf_bpa.py`** — Agora usam `config.py` em vez de valores hardcoded para Firebird.
- **`planilha_nuvem.py`** — Agora usa `config.py` para Google Sheet ID, escopos e caminho do SQLite.
- **`integracao/gerador_arquivo_bpa.py`**, **`integracao/gerador_csv.py`** — Agora usam `config.py` para CNS_PROFISSIONAL e códigos BPA.
- **`.gitignore`** — Adicionado `/scripts/*.txt`.

### Fixed
- **Build GitHub Actions:** movido `--onefile` do comando `pyinstaller` para dentro dos `.spec` files (`onefile=True`).
- **Renomeado** `ideias.md` → `backlog.md` + criado `CHANGELOG.md` separado.

## [2026-05-16]

### Added
- **Startup scripts:** `iniciar_painel.bat` + `start_painel.vbs` (Painel, porta 8001)
- **Startup scripts:** `iniciar_recepcao.bat` + `start_recepcao.vbs` (Recepção, porta 8000)
- Busca automática por Python em múltiplos caminhos (PATH, `%LOCALAPPDATA%`)
- Verificação de porta antes de iniciar (evita servidor duplicado)

### Changed
- `iniciar.bat` e `start.vbs` atualizados para apontar ao Painel (compatibilidade)
- `corrigir_data.py` movido para `scripts/`

### Changed
- `.bat` files agora **matam o processo atual** na porta antes de reiniciar (taskkill)
- `README.md` — instruções de build removidas, substituídas por atalhos .vbs

### Removed
- `.spec` files e `build.yml` (não serão mais usados)
- `.exe` da release v1.1.0 removidos manualmente do GitHub
- `requests` das dependências (não era usado)

## [2026-05-16] — Sessão 3

### Added
- `registro/README.md` — registro de sessão para continuidade entre conversas

### Changed
- **9 scripts renomeados** para maior clareza:
  - `banco_de_dados_hospital_bpa.py` → `sincronizar_firebird.py`
  - `nacionalidade_gdb.py` → `corrigir_nulls.py`
  - `gerador_arquivo_bpa.py` → `exportar_bpa.py`
  - `gerador_csv.py` → `converter_csv.py`
  - `cns_validator_tool.py` → `validar_cns.py`
  - `att_sexo.py` → `atualizar_sexo.py`
  - `cpf_bpa.py` → `sinc_nome.py`
  - `gerar_txt_fusao.py` → `relatorio_fusao.py`
  - `sonda_db.py` → `inspecionar_db.py`
- Todos os imports em `app_painel.py` atualizados para os novos nomes
- Todos os READMEs, docstrings e diagramas atualizados

### Fixed
- `scripts/corrigir_data.py`, `integracao/corrigir_nulls.py`, `integracao/duplicatas_gdb.py` — adicionado `sys.path.append` para rodarem standalone

### Changed
- `weasyprint` → `fpdf2` (elimina dependência de GTK3)
- `auditoria_periodica.py` e `analise_anual_csv.py` reescritos com fpdf2 (mesmo layout, zero dependência externa)

### Removed
- `build_exe.bat` e `main.spec` (obsoletos)
- `scripts/sinc_nome.py` (código duplicado — `sincronizar_firebird.py` faz o mesmo)
- `requirements.txt`/`pyproject.toml`: `weasyprint` removido, `fpdf2` adicionado

## [2026-05-15] — Sessão 4

### Changed
- `README.md` — removida referência a `sinc_nome.py`; WeasyPrint → fpdf2 na lista de tecnologias
- `scripts/README.md` — removida seção `sinc_nome.py`; renumeração 8→7, 9→8
- `backlog.md` — itens de `sinc_nome.py` e WeasyPrint marcados como concluídos
- `pyproject.toml` — `weasyprint` → `fpdf2`

### Removed
- `scripts/sinc_nome.py` (duplicata de `integracao/sincronizar_firebird.py`)

### Security
- Verificado: `credentials.json` **nunca** foi commitado ao Git (`.gitignore` já protegia)
- Verificado: nenhum CSV/TXT de paciente está trackeado (apenas `requirements.txt`)
