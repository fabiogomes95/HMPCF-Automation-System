# HMPCF Automation System

> Hospital automation system for patient check-in, SUS/BPA billing,
> administrative management and audit. Built for a real hospital in
> Extremoz/RN, Brazil.

Sistema de automação hospitalar desenvolvido para otimizar processos
operacionais, recepção, integração BPA/SUS, auditoria e fluxos
administrativos em ambiente hospitalar real.

---

## Visão Geral

O HMPCF Automation System integra recepção digital, automação BPA/SUS,
painel de gestão, auditoria e sincronização com Google Sheets, reduzindo
retrabalho manual e eliminando fichas em papel no Hospital Municipal
Pres. Café Filho (Extremoz/RN).

## Funcionalidades

- **Recepção Digital** — Cadastro de pacientes com busca por CPF, SUS ou
  nome, validação automática de CPF e CNS, registro de atendimentos
- **Automação BPA/SUS** — Geração de arquivos TXT posicionais, exportação
  de lotes e digitação automática via RPA (PyAutoGUI)
- **Painel de Gestão** — Indicadores em tempo real, integração com
  Firebird (sistema legado), consulta de atendimentos paginada,
  backup automático e exportação de relatórios Excel/PDF
- **Auditoria** — Verificação de inconsistências, log centralizado de
  operações e rastreabilidade completa
- **Sincronização** — "Gari da Nuvem": envio automático de atendimentos
  para Google Sheets a cada 10 segundos

---

## Arquitetura

```
📦 HMPCF-Automation-System
 ┣ 📂 analise/                 # BI — Dashboards, relatórios Excel e PDF
 ┣ 📂 automacao/               # RPA — Robô digitador + Scripts de reparo
 ┃  ┣ 📜 executor_rpa.py      # Robô de digitação BPA (PyAutoGUI)
 ┃  ┣ 📜 MIGRAR_PACIENTES.py   # Migração SQLite → Firebird (CADCNS)
 ┃  ┣ 📜 REPARAR_FIREBIRD.py   # Reparo de registros corrompidos no Firebird
 ┃  ┣ 📜 padronizar_firebird.py# Padronização de campos CADCNS
 ┃  ┣ 📜 digitacao.py          # Geração de arquivos de produção TXT
 ┃  ┗ 📜 limpeza.py            # Extração/validação de CPF e CNS
 ┣ 📂 integracao/              # Integração SUS — conversores TXT
 ┣ 📂 scripts/                 # Scripts administrativos e manutenção
 ┣ 📂 web_recepcao/            # Frontend da Recepção (porta 8000)
 ┣ 📂 web_painel/              # Frontend do Painel de Gestão (porta 8001)
 ┣ 📂 hmcpf-system/            # Backend FastAPI (nova arquitetura)
 ┣ 📜 app_recepcao.py          # Servidor da Recepção (Eel)
 ┣ 📜 app_painel.py            # Servidor do Painel de Gestão (Eel)
 ┣ 📜 main.py                  # Launcher unificado
 ┣ 📜 config.py                # Configuração centralizada
 ┣ 📜 planilha_nuvem.py        # Sincronizador Google Sheets
 ┗ 📜 passo_a_passo.md         # Setup completo para nova máquina
```

---

## O que foi feito nesta sessão (18/05/2026)

### Scripts criados

| Script | Função |
|--------|--------|
| `automacao/MIGRAR_PACIENTES.py` | Migração definitiva SQLite → Firebird com geração manual de ID, valores fixos, tratamentos de nulos e verificação de duplicidade |
| `automacao/REPARAR_FIREBIRD.py` | Ferramenta de reparo de registros corrompidos no CADCNS (IDs nulos, endereços vazios, sexo inválido, etc.) |
| `automacao/padronizar_firebird.py` | Padronização standalone de campos do CADCNS (LOGPCN, NUMPCN, etc.) |
| `integracao/padronizar.py` | Padronização da tabela SQLite |

### Correções e melhorias

| Arquivo | Mudança |
|---------|---------|
| `executor_rpa.py` | Troca `fdb` → `firebirdsql` (compatibilidade 64-bit). Adiciona `manter_acordado()` para evitar suspensão do Windows durante RPA Consulta em RAM (`_buscar_na_ram`) para acelerar preparação de lotes |
| `limpeza.py` | Algoritmo de validação CNS corrigido (dígito verificador completo) |
| `app_painel.py` | Import corrigido de `cpf_sus` → `limpeza`. Base de pacientes recarregada automaticamente |
| `cadcns_repository.py` | Nova função `buscar_por_documento()` |
| `robo_service.py` | Novas funções `buscar_paciente_no_banco()`, `preparar_lotes()`, `executar_pyautogui()` |
| `processamento_service.py` | Nova função `processar_lista()` para extrair CPF/SUS |
| `web_painel/robo.html` | Botão "Iniciar Automação" agora com `onclick` funcional |
| `.env.example` | Configurações de produção descomentadas |
| `requirements.txt` / `pyproject.toml` | Adicionadas dependências: `fdb`, `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy` |

---

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação
em produção sem autorização explícita do autor.
