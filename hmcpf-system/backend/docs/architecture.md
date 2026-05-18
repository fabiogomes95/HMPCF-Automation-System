# Arquitetura do Backend — HMPCF

## Estrutura de Camadas

```
modules/        → Roteadores FastAPI (controllers)
  ├── recepcao/     → CRUD pacientes + atendimentos
  ├── bpa/          → Produção, lotes, RPA, exportação
  └── integracao/   → CSV, Firebird, contingência, backup
       │
       ▼
services/       → Lógica de negócio (orquestração)
  ├── recepcao/     → paciente_service, atendimento_service, busca_service
  ├── bpa/          → producao_service, processamento_service, robo_service,
  │                   exportacao_service, validacao_service
  └── integracao/   → importacao_service, sincronizacao_service, limpeza_service,
                      contingencia_service, auditoria_service, utils
       │
       ▼
repositories/   → Acesso a dados (SQL puro)
  ├── paciente_repository.py
  ├── atendimento_repository.py
  ├── producao_repository.py
  └── cadcns_repository.py
       │
       ▼
database/       → Conexões e helpers de banco
  ├── legacy.py      → SQLite (hospital.db)
  └── firebird.py    → Firebird (BPAMAG.GDB)
```

## Responsabilidades por Módulo

### recepcao
- `/pacientes` — CRUD completo com paginação, busca por nome/CPF, detecção de duplicatas
- `/atendimentos` — listagem com filtros por CPF e data, criação
- `/busca` — busca unificada de pacientes (nome, CPF, CNS)

### bpa
- `/producao` — gerenciamento de arquivos .txt de produção, lotes por enfermeiro
- `/processamento/triagem` — extrai CPF/CNS de texto bruto, valida contra Firebird
- `/robo` — controle do robô RPA (PyAutoGUI), preparação/execução/monitoramento
- `/exportar` — exportação de dados do SQLite para formato BPA (DATASUS)
- `/validacao` — funções de validação de CNS, CPF (puras, sem I/O)

### integracao
- `/importar/csv` — importação smart-update de CSV (novos + parciais + ignorados)
- `/converter/csv` — conversão de CSV antigo → TXT BPA
- `/exportar/bpa` — exporta SQLite → TXT BPA
- `/sincronizar/firebird` — padroniza dados no BPAMAG.GDB (acentos, telefones)
- `/limpeza/firebird/nulls` — corrige NULLs no CADCNS
- `/limpeza/firebird/duplicatas` — remove duplicatas no CADCNS
- `/contingencia` — sincroniza CSV de contingência com hospital.db
- `/backup` — backup/restore de arquivos

## Fluxo de Dados

1. **Cliente → FastAPI Router** → validação de parâmetros
2. **Router → Service** → orquestra lógica de negócio
3. **Service → Repository** → consulta/insere dados
4. **Repository → Database (legacy/firebird)** → SQL puro

## Padrões

- **Repository Pattern**: toda query SQL fica em repositories/. Services nunca usam SQL direto.
- **Services stateless**: serviços são módulos de funções, sem classes. Conexão é recebida do database/ e fechada no service.
- **Compat Layer**: `modules/` importa de `services/`. Alguns módulos antigos em `modules/integracao/service.py` re-exportam funções de `services/integracao/` para compatibilidade retroativa.
- **Validation**: funções de validação puras (sem I/O) em `services/bpa/validacao_service.py` e `services/integracao/utils.py`.

## Limpeza Realizada (Maio/2026)

- Extração de `database/legacy.py` e `database/firebird.py` de dentro de `modules/`
- Criação de `repositories/` com 4 repositórios isolando todo SQL
- Criação de `services/recepcao/`, `services/bpa/`, `services/integracao/` com lógica de negócio
- `modules/` convertido para compat layers; rotas intactas (35 rotas, sem quebras)
- Remoção de `_row_to_dict` duplicado (padronizado para `dict(row)`)
- Remoção de imports mortos
- 11 testes unitários passando
