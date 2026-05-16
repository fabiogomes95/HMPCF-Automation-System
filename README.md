# HMPCF Automation System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Status](https://img.shields.io/badge/status-produção-green)

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

### Problema

Antes do sistema, a recepção usava fichas de papel, os lançamentos BPA
eram feitos manualmente um a um, a auditoria era feita em planilhas
soltas e não havia sincronização entre os setores.

### Solução

Um sistema integrado que digitaliza o fluxo da recepção, automatiza a
geração de lotes BPA/SUS, centraliza a auditoria e sincroniza os dados
com a nuvem — tudo acessível via navegador nas estações do hospital.

---

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

```mermaid
flowchart LR
A[Recepção Digital] --> B[SQLite Local]
B --> C[Painel Administrativo]
B --> D[Automação BPA/SUS]
D --> E[Triagem e Fila]
E --> F[Auditoria]
F --> G[Relatórios Excel/PDF]
B --> H[Google Sheets]
```

```text
📦 HMPCF-Automation-System
 ┣ 📂 analise/                 # BI — Dashboards e relatórios
 ┣ 📂 automacao/               # RPA — digitação automatizada
 ┣ 📂 integracao/              # Conversores TXT e sincronizadores
 ┣ 📂 scripts/                 # Ferramentas administrativas
 ┣ 📂 web_recepcao/            # Frontend da Recepção (porta 8000)
 ┣ 📂 web_painel/              # Frontend do Painel (porta 8001)
 ┣ 📜 app_recepcao.py          # Servidor da Recepção (Eel)
 ┣ 📜 app_painel.py            # Servidor do Painel (Eel)
 ┣ 📜 main.py                  # Launcher unificado
 ┣ 📜 config.py                # Configuração centralizada
 ┣ 📜 planilha_nuvem.py        # Sincronizador Google Sheets
 ┣ 📜 utils.py                 # Validações (CPF, CNS)
 ┗ 📜 .env.example             # Template de configuração
```

---

Desenvolvido por [Fabio Gomes](https://www.linkedin.com/in/fabiogsilva95/)

## Licença

Copyright (c) 2026 Fabio Gomes. Todos os direitos reservados.

Disponível publicamente para fins de estudo, demonstração técnica e
portfólio. Não é permitido uso comercial, institucional ou implantação
em produção sem autorização explícita do autor.
