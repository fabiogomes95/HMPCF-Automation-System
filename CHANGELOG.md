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

### Removed
- `.spec` files e `build.yml` (não serão mais usados)
- `.exe` da release v1.1.0 removidos manualmente do GitHub
