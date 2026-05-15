# Ideias para o HMPCF

> Anotações de funcionalidades desejadas, melhorias e pendências.

## 📌 Pendências

- [ ] **credentials.json** — Remover do histórico do Git (vazamento de chave Google) e trocar a chave no Google Cloud
- [ ] **Arquivos com dados reais** — Remover ou ignorar CSVs/TXTs com dados de pacientes do repositório (privacidade)
- [ ] **Senhas centralizadas** — Criar `config.py` ou `.env` para senhas do Firebird (`SYSDBA`/`masterkey`) e Google Sheets em vez de espalhar em 5+ arquivos
- [ ] **Código duplicado** — `archive/cpf_bpa.py` é cópia de `integracao/banco_de_dados_hospital_bpa.py`. Decidir se mantém ou apaga
- [ ] **WeasyPrint / GTK3** — Trocar por alternativa sem dependência externa (matplotlib, Pillow ou fpdf2)

## 💡 Ideias Futuras

- [ ] **Estrutura de pacote Python** — Substituir `sys.path.append` por `pyproject.toml` para imports limpos
- [ ] **Config centralizada** — Mover Firebird paths, Google Sheet ID, portas para um único `config.py`
- [ ] **Mover `corrigir_data.py`** para dentro de `integracao/` (já mexe no Firebird)
- [ ] **Type hints** — Adicionar tipos nos arquivos Python
- [ ] **Logging** — Trocar `print()` por logging module
- [ ] **Remover `requests`** das dependências (não é usado, só `urllib`)
- [ ] **Renomear `archive/`** para `scripts/` ou `tools/` (não é só lixo)
- [ ] **Connection pool** para Firebird nas integrações
