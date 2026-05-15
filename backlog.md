# Backlog — HMPCF Automation System

> Pendências, melhorias e ideias futuras para o projeto.

## 📌 Pendências

- [ ] **credentials.json** — Remover do histórico do Git (vazamento de chave Google) e trocar a chave no Google Cloud
- [ ] **Arquivos com dados reais** — Remover ou ignorar CSVs/TXTs com dados de pacientes do repositório (privacidade)
- [x] **Senhas centralizadas** — Criado `config.py` + `.env.example` (Firebird, Google Sheets, CNS, códigos BPA)
- [x] **Código duplicado** — `scripts/sinc_nome.py` removido (manter `integracao/sincronizar_firebird.py`)
- [x] **WeasyPrint / GTK3** — Substituído por fpdf2 (zero dependência externa)

## 💡 Ideias Futuras

- [x] **Estrutura de pacote Python** — Criado `pyproject.toml` para imports limpos
- [x] **Config centralizada** — Firebird paths, Google Sheet ID, CNS_PROFISSIONAL movidos para `config.py`
- [x] **Mover `corrigir_data.py`** para `scripts/` (concluído)
- [x] **Type hints** — Adicionados em todas as funções dos 35 arquivos `.py`
- [x] **Logging** — `print()` substituído por `logging_setup.logger` em 27 arquivos
- [x] **Remover `requests`** das dependências (não era usado)
- [x] **Renomear `archive/`** para `scripts/` (concluído)
- [] **Verificar o  `/registro/`** readme.md e nosso changelog.md! ficou faltando salvar algumas coisas que foram efetuadas pq o pc desligou. O meu web_recepção index.html agora tem um botao pra mudo escuro so que ele ficou em cima da informção que diz: "online"

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