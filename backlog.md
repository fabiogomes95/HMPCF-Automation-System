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
- [ ] **Type hints** — Adicionar tipos nos arquivos Python
- [x] **Logging** — `print()` substituído por `logging_setup.logger` em 27 arquivos
- [x] **Remover `requests`** das dependências (não era usado)
- [x] **Renomear `archive/`** para `scripts/` (concluído)
- [ ] **Connection pool** para Firebird nas integrações
