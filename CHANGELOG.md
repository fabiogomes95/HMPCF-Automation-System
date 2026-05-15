# Changelog

## [2026-05-15]

### Added
- **`config.py`** — Configuração centralizada lendo de `.env` (Firebird, Google Sheets, BPA).
- **`.env.example`** — Template para configuração local (não contém senhas reais).
- **`pyproject.toml`** — Estrutura de pacote Python (pip install -e .).
- **`__init__.py`** com docstrings nos pacotes `automacao/`, `analise/`, `integracao/`, `scripts/`.

### Changed
- **`archive/` → `scripts/`** — Renomeado diretório e atualizadas todas as referências nos docstrings.
- `limpar_clones.py` movido da raiz para `scripts/`.
- `scripts/faxina.py` renomeado para `scripts/faxina_sqlite.py` para indicar o uso do banco SQLite nativo do Python.
- Raiz `faxina.py` movido para `scripts/faxina_firebird.py` para manter o script Firebird separado.
- **`app_painel.py`**, **`corrigir_data.py`**, **`integracao/banco_de_dados_hospital_bpa.py`**, **`integracao/duplicatas_gdb.py`**, **`integracao/nacionalidade_gdb.py`**, **`scripts/cpf_bpa.py`** — Agora usam `config.py` em vez de valores hardcoded para Firebird.
- **`planilha_nuvem.py`** — Agora usa `config.py` para Google Sheet ID, escopos e caminho do SQLite.
- **`integracao/gerador_arquivo_bpa.py`**, **`integracao/gerador_csv.py`** — Agora usam `config.py` para CNS_PROFISSIONAL e códigos BPA.
- **`.gitignore`** — Adicionado `/scripts/*.txt`.
 - **`app_painel.py`** — Autenticação admin refinada: `set_admin` agora cria sessão com tempo de expiração, `is_admin` valida/expira sessão automaticamente e `logout_admin` foi adicionado.
 - **`config.py`** — Nova opção `ADMIN_SESSION_MINUTES` para controlar duração da sessão admin (padrão 15 minutos).
 - **`web_painel/integracao.html`** — UI: badge de status `Admin: on/off`, botão `Logout` e polling para atualizar o status; modal de autenticação admin mantido.
 - **`backlog.md`** — Atualizado automaticamente com entradas sobre autenticação admin (status-only logging) e implementação de timeout.

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

## [2026-05-15] — Sessão 5

### Added
- **`logging_setup.py`** — Módulo centralizado de logging com formato timestamp + nível (`logging.getLogger("hmpcf")`)

### Changed
- **Todos os 27 arquivos com `print()`** agora usam `logging_setup.logger` com nível adequado:
  - `automacao/digitacao.py`, `automacao/executor_rpa.py`
  - `planilha_nuvem.py`
  - `app_painel.py`, `app_recepcao.py`
  - `main.py` (helpers `info/sucesso/aviso/erro` agora usam `logger.info/warning/error`)
  - `analise/analise_anual_csv.py`, `analise/auditoria_periodica.py`, `analise/dashboard_visual.py`, `analise/historico_paciente.py`, `analise/planilha_producao.py`
  - `integracao/converter_csv.py`, `integracao/corrigir_nulls.py`, `integracao/duplicatas_gdb.py`, `integracao/exportar_bpa.py`, `integracao/importador_recepcao.py`, `integracao/sincronizar_contingencia.py`, `integracao/sincronizar_firebird.py`
  - `scripts/atualizar_sexo.py`, `scripts/auditor_bpa.py`, `scripts/corrigir_data.py`, `scripts/corrigir_sexo_bpa.py`, `scripts/faxina_sqlite.py`, `scripts/fusao.py`, `scripts/inspecionar_db.py`, `scripts/relatorio_fusao.py`, `scripts/validar_cns.py`
- `backlog.md` — item de logging marcado como concluído

## [2026-05-15] — Sessão 6

### Added
- **Type hints** em todas as funções dos 35 arquivos `.py`:
  - Parâmetros tipados (`str`, `int`, `bool`, `list[dict]`, `str | None`, etc.)
  - Retornos tipados (`-> None`, `-> str`, `-> bool`, `-> list[dict]`, etc.)
  - Uso de `from typing import Callable, Final` onde necessário

### Removed
- **Connection pool** removido do `backlog.md` (cancelado — não agrega valor, Firebird usado apenas esporadicamente)

### Changed
- `backlog.md` — type hints marcado como concluído, connection pool cancelado
