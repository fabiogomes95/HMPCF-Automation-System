# Backlog — HMPCF Automation System

> Pendências, melhorias e ideias futuras para o projeto.

## 📌 Pendências

- [ ] **credentials.json** — Remover do histórico do Git (vazamento de chave Google) e trocar a chave no Google Cloud
- [ ] **Arquivos com dados reais** — Remover ou ignorar CSVs/TXTs com dados de pacientes do repositório (privacidade)
- [x] **Senhas centralizadas** — Criado `config.py` + `.env.example` (Firebird, Google Sheets, CNS, códigos BPA)
- [x] **Senhas sem default hardcoded** — `config.py` agora exige `FIREBIRD_PASSWORD`, `GOOGLE_SHEET_ID`, `CEP_RUA`, `CODIGO_UNIDADE`, `ADMIN_PASSWORD` via `_require_env()`, falhando no startup se ausentes.
- [x] **Senha admin hasheada** — `set_admin_password()` armazena SHA256; `set_admin()` compara hash; compatibilidade com `.admin_pass` legado.
- [x] **Código duplicado** — `scripts/sinc_nome.py` removido (manter `integracao/sincronizar_firebird.py`)
- [x] **WeasyPrint / GTK3** — Substituído por fpdf2 (zero dependência externa)

## 💡 Ideias Futuras

- [x] **Estrutura de pacote Python** — Criado `pyproject.toml` para imports limpos
- [x] **Config centralizada** — Firebird paths, Google Sheet ID, CEP_RUA, CODIGO_UNIDADE movidos para `config.py`
- [x] **Mover `corrigir_data.py`** para `scripts/` (concluído)
- [x] **Type hints** — Adicionados em todas as funções dos 35 arquivos `.py`
- [x] **Logging** — `print()` substituído por `logging_setup.logger` em 27 arquivos
- [x] **Remover `requests`** das dependências (não era usado)
- [x] **Renomear `archive/`** para `scripts/` (concluído)
- [x] **Verificar o `/registro/`** readme.md e nosso changelog.md — ok, arquivos conferidos e consistentes.
- [x] **README.md corrigido** — imagens de screenshots quebradas removidas e substituídas por texto descritivo; `local_database.db` → `hospital.db`; `google_credentials.example.json` → `credentials.json`.
- [x] **web_recepcao/style.css** — overlap do botão modo escuro com indicador Online corrigido: removido `flex-wrap: wrap` e adicionado `flex-shrink: 0` nos filhos da `.status-bar`.
- [x] **MD031 em 6 arquivos .md** — adicionadas linhas em branco antes/após blocos de código em: `analise/README.md`, `integracao/README.md`, `registro/README.md`, `registro/relatorio_revisao_HMPCF.md`, `scripts/README.md`.

## ✅ Alterações recentes (sincronizadas automaticamente)

- [x] Mover `limpar_clones.py` da raiz para `scripts/`.
- [x] Renomear `scripts/faxina.py` → `scripts/faxina_sqlite.py`.
- [x] Mover `faxina.py` (raiz) → `scripts/faxina_firebird.py`.
- [x] Proteger operações sensíveis no painel: `corrigir_nulls`, `duplicatas_gdb` (admin-only).
- [x] Adicionar suporte admin no backend (`app_painel.set_admin`, `is_admin`) e modal no frontend para autenticação.
- [x] Tornar `sincronizar_firebird` operação admin-only.
- [x] Registrar tentativas de autenticação admin no `auditoria_log` e em `logger`.
- [x] Confirmado: não registrar username (apenas status/resultado da autenticação admin é logado).
- [x] Implementado timeout de sessão admin (`ADMIN_SESSION_MINUTES`), endpoint `logout_admin` e badge de status no painel.
- [x] Painel de integração iniciado **fechado** por padrão com overlay de cadeado; botão `Desbloquear` exige autenticação admin.
- [x] Senha padrão do painel definida como `8878` quando não configurada; agora é possível alterar a senha pelo próprio painel (menu `Alterar senha`).
- [x] Corrigido overlap do botão modo noturno com o indicador `Online` em `web_painel/index.html` e terminal de eventos agora exibe entradas reais do `auditoria.log`.
- [x] **config.py**: criado helper `_require_env()` com falha explícita; defaults hardcoded removidos para `FIREBIRD_PASSWORD`, `GOOGLE_SHEET_ID`, `CEP_RUA`, `CODIGO_UNIDADE`, `ADMIN_PASSWORD`.
- [x] **config.py + app_painel.py**: senha admin armazenada como SHA256 hash (via `_hash_password`); `set_admin()` no painel compara hash; fallback compatível com `.admin_pass` legado em texto plano.
- [x] **app_recepcao.py**: `conectar_banco()` ativa WAL mode (`PRAGMA journal_mode=WAL`); `buscar_paciente()`, `buscar_por_nome()`, `buscar_historico()`, `verificar_duplicata()` agora garantem `conn.close()` via `finally`.
- [x] **planilha_nuvem.py**: Gari da Nuvem limpa locks fantasmas (`enviado_nuvem=2`) na inicialização, evitando registros permanentemente travados após crash.
- [x] **app_painel.py**: variável global `IS_ADMIN` inicializada como `False` na raiz do módulo, prevenindo `NameError` em operações admin-only antes do primeiro login.
- [x] **planilha_nuvem.py**: autenticação Google refatorada para singleton (`_get_gsuite()`) com `AuthorizedSession`, eliminando recriação de credenciais a cada envio.
- [x] **app_recepcao.py (`salvar`)**: CPF e CNS/CUS validados via `valida_cpf()` e `valida_cns()` antes de inserir no banco; retorna erro ao frontend se inválidos.
- [x] **app_recepcao.py (`buscar_por_nome`)**: caracteres `%` e `_` sanitizados com `ESCAPE '\'` para evitar vazamento de dados via LIKE injection.
- [x] **main.py**: `input()` substituído por `_is_interactive()` — pula perguntas em modo serviço (sem terminal).
- [x] **main.py (`fazer_update_zip`)**: arquivos `.py` não são mais copiados com o processo rodando; são adiados para a próxima inicialização via marcador `.update_pending`, aplicados por `_aplicar_update_pendente()` antes de qualquer import do projeto.