# Backlog — HMPCF Automation System

> Pendências, melhorias e ideias futuras para o projeto.

## 📌 Pendências

- [ ] **credentials.json** — Remover do histórico do Git (vazamento de chave Google) e trocar a chave no Google Cloud
- [ ] **Arquivos com dados reais** — Remover ou ignorar CSVs/TXTs com dados de pacientes do repositório (privacidade)
- [x] **Senhas centralizadas** — Criado `config.py` + `.env.example` (Firebird, Google Sheets, CNS, códigos BPA)
- [ ] **Código duplicado** — `scripts/cpf_bpa.py` é cópia de `integracao/banco_de_dados_hospital_bpa.py`. Decidir se mantém ou apaga
- [ ] **WeasyPrint / GTK3** — Trocar por alternativa sem dependência externa (matplotlib, Pillow ou fpdf2)

## 💡 Ideias Futuras

- [x] **Estrutura de pacote Python** — Criado `pyproject.toml` para imports limpos
- [x] **Config centralizada** — Firebird paths, Google Sheet ID, CNS_PROFISSIONAL movidos para `config.py`
- [ ] **Mover `corrigir_data.py`** para dentro de `integracao/` (já mexe no Firebird)
- [ ] **Type hints** — Adicionar tipos nos arquivos Python
- [ ] **Logging** — Trocar `print()` por logging module
- [ ] **Remover `requests`** das dependências (não é usado, só `urllib`)
- [x] **Renomear `archive/`** para `scripts/` (concluído)
- [ ] **Connection pool** para Firebird nas integrações
