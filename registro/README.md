# Registro de Sessão — HMPCF Automation System

> Arquivo criado para manter continuidade entre sessões.
> Use este arquivo como referência quando retomar o trabalho.

---

## Sessão 1 — 2026-05-15

### Problema resolvido: Build .exe falhando no GitHub Actions
**Erro:** `pyinstaller recepcao.spec --onefile` — `--onefile` é flag de makespec, não aceita quando .spec é passado.
**Solução:** Movido `onefile=True` para dentro dos .spec files (`recepcao.spec`, `painel.spec`). Removido `--onefile` do `build.yml`.

### Renomeação de arquivos
- `ideias.md` → `backlog.md` (pendências e ideias futuras)
- Criado `CHANGELOG.md` (histórico de alterações)

### Organização do código
**Arquivos alterados para usar `config.py`:**
- `app_painel.py` — Firebird user/password/path
- `planilha_nuvem.py` — Google Sheet ID, escopos, caminho SQLite
- `corrigir_data.py` — Firebird credenciais
- `integracao/sincronizar_firebird.py` — Firebird credenciais
- `integracao/duplicatas_gdb.py` — Firebird credenciais
- `integracao/corrigir_nulls.py` — Firebird credenciais
- `integracao/exportar_bpa.py` — CNS_PROFISSIONAL, CBO, etc.
- `integracao/converter_csv.py` — CNS_PROFISSIONAL, CBO, etc.
- `scripts/sinc_nome.py` — Firebird credenciais

**Arquivos criados:**
- `config.py` — lê `.env` ou usa defaults (sem `.env` o sistema funciona igual)
- `.env.example` — template comentado
- `pyproject.toml` — estrutura de pacote Python
- `__init__.py` com docstrings em `automacao/`, `analise/`, `integracao/`, `scripts/`

**Diretórios renomeados:**
- `archive/` → `scripts/` (sem quebra de imports)

**Removido:**
- `.spec` files (`painel.spec`, `recepcao.spec`, `main.spec`)
- `.github/workflows/build.yml`
- `.exe` da release `v1.1.0` (3 arquivos: HMPCF.exe, HMPCF_Painel.exe, HMPCF_Recepcao.exe)

---

## Sessão 2 — 2026-05-16

### Startup scripts para Windows 11
**Criados para iniciar cada servidor separadamente:**

| Arquivo | Função |
|---|---|
| `iniciar_painel.bat` | Inicia Painel (porta 8001) com pythonw |
| `iniciar_recepcao.bat` | Inicia Recepção (porta 8000) com pythonw |
| `start_painel.vbs` | Executa `iniciar_painel.bat` invisível |
| `start_recepcao.vbs` | Executa `iniciar_recepcao.bat` invisível |

**Removidos:** `iniciar.bat`, `start.vbs` (substituídos pelos específicos)

**Movido:** `corrigir_data.py` → `scripts/`

### Instruções para criar atalhos no Windows 11
1. Botão direito na Área de Trabalho → Novo → Atalho
2. **Painel:** `wscript.exe "C:\caminho\HMPCF-Automation-System\start_painel.vbs"`
3. **Recepção:** `wscript.exe "C:\caminho\HMPCF-Automation-System\start_recepcao.vbs"`

### Como usar o sistema sem .exe
- Dar `git pull` em cada máquina do hospital
- Cada máquina precisa ter Python 3.10+ e `pip install -r requirements.txt`
- O `hospital.db` fica na raiz do projeto (cada máquina tem o seu)
- `credentials.json` precisa estar na raiz (Google Sheets)

### Arquitetura atual
```
HMPCF-Automation-System/
├── app_painel.py          # Servidor web Painel (porta 8001)
├── app_recepcao.py        # Servidor web Recepção (porta 8000)
├── config.py              # Config centralizada (Firebird, Google, BPA)
├── .env.example           # Template de configuração (opcional)
├── automacao/             # RPA, CPF/SUS, digitação
├── integracao/            # Firebird sync, BPA export, CSV import
├── analise/               # BI: dashboards, relatórios, auditoria
├── scripts/               # Ferramentas DBA: faxina, fusão, validação
├── web_painel/            # Frontend do Painel (HTML/JS)
├── web_recepcao/          # Frontend da Recepção (HTML/JS)
├── hospital.db            # SQLite local (pacientes + atendimentos)
├── credentials.json       # Chave Google Cloud (não versionada)
├── requirements.txt       # Dependências Python
└── pyproject.toml         # Estrutura de pacote
```

### Portas
- **8000** — Recepção (cadastro de pacientes)
- **8001** — Painel de Gestão (BI, RPA, integração Firebird)

### Banco de dados Firebird
- **Caminho:** `C:/BPA/BPAMAG.GDB`
- **Usuário:** `SYSDBA`
- **Senha:** `masterkey`
- **Host:** `localhost`
- Tudo configurável via `.env` se necessário

### Google Sheets (Gari da Nuvem)
- **credentials.json** — serviço Google Cloud (já na pasta)
- **Sheet ID:** `1xw_x-bYlHCHzMe39g1mJKPFAD_IcXA8BB0uRfmmuR90`
- Sincroniza atendimentos da recepção em tempo real

---

## Sessão 3 — 2026-05-16 (continuação)

### Renomeação de scripts (9 arquivos)

| Nome antigo | Nome novo | Motivo |
|---|---|---|
| `integracao/banco_de_dados_hospital_bpa.py` | `integracao/sincronizar_firebird.py` | Muito longo (34 chars) |
| `integracao/nacionalidade_gdb.py` | `integracao/corrigir_nulls.py` | Nome enganava (não é sobre nacionalidade) |
| `integracao/gerador_arquivo_bpa.py` | `integracao/exportar_bpa.py` | Mais direto |
| `integracao/gerador_csv.py` | `integracao/converter_csv.py` | "gerador" não descrevia a função |
| `scripts/cns_validator_tool.py` | `scripts/validar_cns.py` | PT/EN misturado |
| `scripts/att_sexo.py` | `scripts/atualizar_sexo.py` | Abreviação pouco clara |
| `scripts/cpf_bpa.py` | `scripts/sinc_nome.py` | "cpf_bpa" não explicava que sincroniza por nome |
| `scripts/gerar_txt_fusao.py` | `scripts/relatorio_fusao.py` | "gerar_txt" é detalhe técnico |
| `scripts/sonda_db.py` | `scripts/inspecionar_db.py` | "sonda" muito informal |

### Bugs corrigidos
- `scripts/corrigir_data.py`, `integracao/corrigir_nulls.py`, `integracao/duplicatas_gdb.py` — faltava `sys.path.append`, quebravam quando rodados standalone
- `README.md` — diagrama desatualizado (mostrava `corrigir_data.py` na raiz, faltavam arquivos)

### Arquivos removidos
- `build_exe.bat` e `main.spec` (obsoletos após abandonar build .exe)
- `requests` removido do `requirements.txt` (não era usado)

### .bat agora matam processo antes de reiniciar
- `iniciar_painel.bat` e `iniciar_recepcao.bat` agora dão `taskkill /f` no processo atual da porta antes de subir novo servidor

### Revisão final da arquitetura
- **38 arquivos Python**
- **4 pacotes**: `automacao/`, `integracao/`, `analise/`, `scripts/`
- **Zero hardcoded credentials** fora do `config.py`
- **Todos os imports verificados** — nenhum quebrado
- **3 arquivos com `from config import ...`** corrigidos para funcionar standalone

---

## Sessão 5 — 2026-05-15 — Logging: print() → logging module

### O que foi feito
- Criado `logging_setup.py` — módulo centralizado de logging (timestamp + nível + stdout)
- Substituído `print()` por `logger.info()`, `logger.warning()`, `logger.error()` em **todos os 27 arquivos** que usavam print
- Cada `print()` classificado por nível:
  - `logger.error()` — exceptions, erros de banco, falhas críticas
  - `logger.warning()` — avisos, cancelamentos, dados não encontrados
  - `logger.info()` — tudo o resto (progresso, sucesso, banners)
- `main.py` — helpers `info()`, `sucesso()`, `aviso()`, `erro()` mantidos mas agora usam `logger` internamente (com ANSI colors preservados)
- `backlog.md` — item de logging marcado como concluído

### Formato das mensagens
```
2026-05-15 05:27:04 [INFO] Servidor HMPCF Iniciado...
2026-05-15 05:27:04 [ERROR] Erro ao salvar: ...
```

### Arquivos modificados (27)
- `automacao/`: `digitacao.py`, `executor_rpa.py`
- `raiz/`: `main.py`, `planilha_nuvem.py`, `app_painel.py`, `app_recepcao.py`
- `analise/`: `analise_anual_csv.py`, `auditoria_periodica.py`, `dashboard_visual.py`, `historico_paciente.py`, `planilha_producao.py`
- `integracao/`: `converter_csv.py`, `corrigir_nulls.py`, `duplicatas_gdb.py`, `exportar_bpa.py`, `importador_recepcao.py`, `sincronizar_contingencia.py`, `sincronizar_firebird.py`
- `scripts/`: `atualizar_sexo.py`, `auditor_bpa.py`, `corrigir_data.py`, `corrigir_sexo_bpa.py`, `faxina.py`, `fusao.py`, `inspecionar_db.py`, `relatorio_fusao.py`, `validar_cns.py`

### Pendente
- Nada. Todos os prints substituídos e verificados (syntax check OK nos 35 .py).

---

## Sessão 6 — 2026-05-15 — Type hints em todas as funções

### O que foi feito
- Adicionados type hints em **todas as funções** dos 35 arquivos `.py`
- Parâmetros tipados (`str`, `int`, `bool`, `list[dict]`, `str | None`, `dict`, etc.)
- Retornos tipados (`-> None`, `-> str`, `-> bool`, `-> list[dict]`, etc.)
- `from typing import Callable, Final` adicionados onde necessário
- `config.py`: `_carregar_dotenv() -> None`
- `utils.py`: todas as 5 funções tipadas (`apenas_numeros`, `remove_accents`, `valida_cns`, `parse_endereco_fixed`, `valida_cpf`)
- `logging_setup.py`: `logger: Final`
- `automacao/`: `digitacao.py` (3 funções), `executor_rpa.py` (2 funções), `cpf_sus.py` (1 função)
- `integracao/`: todas as 7 funções principais tipadas
- `analise/`: todas as 11 funções tipadas
- `scripts/`: `corrigir_data.py`, `faxina.py`, `fusao.py`, `relatorio_fusao.py`
- `app_painel.py`: todas as 22 funções `@eel.expose` + `carregar_base()` e `iniciar()`
- `app_recepcao.py`: todas as 11 funções + helpers tipadas
- `main.py`: todas as 9 funções tipadas
- `planilha_nuvem.py`: `enviar_para_planilha()` e `gari_da_nuvem()` tipadas
- Zero mudanças na lógica — só anotações

### Backlog atualizado
- Type hints marcado como concluído ✅
- Connection pool cancelado (não agrega valor — Firebird usado só esporadicamente, RAM cache já resolve)

### Próximos passos possíveis
- Nada urgente. Sistema está completo para o uso atual.

---

## Sessão 7 — 2026-05-15 — Consulta Atendimentos + IBGE raça

### O que foi feito
- **`analise/consulta_recepcao.py`** — Novo módulo com 3 funções:
  - `consultar_atendimentos(data_inicio, data_fim)` → lista completa com JOIN em pacientes
  - `resumo_atendimentos(...)` → total, por procedência, média/dia
  - `atendimentos_por_dia(...)` → daily counts para gráfico
  - Lê do `hospital.db` (SQLite), caminho configurável via `DB_SQLITE` no `.env`
- **`web_painel/consulta.html`** — Página nova (435 linhas) no padrão do painel:
  - Topbar azul igual às outras páginas, link "⬅️ Análise"
  - Filtros de data com atalhos: Hoje, Esta Semana, Este Mês
  - Stats cards: Total, Média/dia, por Procedência, Tipos
  - Gráfico doughnut (Chart.js) — distribuição por procedência
  - Gráfico de barras — atendimentos por dia no período
  - Tabela rolável com sticky header (registro, paciente, CPF, DN, tel)
  - Loading spinner durante a consulta
  - 3 chamadas Eel em paralelo via `Promise.all`
- **`web_painel/analise.html`** — Card "Consulta Atendimentos" adicionado (primeiro da grade)
- **`app_painel.py`** — 3 novos `@eel.expose`:
  - `consulta_listar_atendimentos`
  - `consulta_resumo_atendimentos`
  - `consulta_atendimentos_por_dia`
- **`web_recepcao/index.html`** — Opção "AMARELA" adicionada ao campo Raça/Cor (IBGE 5 categorias: Branca, Preta, Parda, Amarela, Indígena). Layout ajustado naturalmente, empurrando "Ocupação" ligeiramente.
- **`.env.example`** — Documentado `DB_SQLITE` com exemplo de caminho de rede

### Como usar
1. Abrir `app_painel.py` (porta 8001)
2. Navegar para Análise / BI → Consulta Atendimentos
3. Selecionar período (ou usar atalhos) e clicar Consultar
4. Ver cards, gráficos e tabela

### Notas
- `hospital.db` precisa estar acessível de onde o `app_painel.py` roda
- Se for em outra máquina, configurar `DB_SQLITE=\servidor\compartilhado\hospital.db` no `.env`
- Gráficos usam Chart.js 4.4.7 via CDN

---

## Sessão 8 — 2026-05-15 — Backup, auditoria, exportação, indicadores, dark mode, lembrete

### O que foi feito

**6 novos recursos:**

1. **Backup automático** (`integracao/backup_utils.py`)
   - `fazer_backup(caminho, prefixo)` copia arquivo para `backups/` com timestamp
   - Disparado automaticamente antes de: sincronizar_firebird, aniquilar_nulls, limpar_duplicatas
   - Backup manual + listagem via Eel

2. **Log de auditoria** (`auditoria_log.py`)
   - `registrar(acao, detalhes)` append JSON Lines em `auditoria.log`
   - Toda ação importante registrada (início do painel, relatórios, BPA, RPA)
   - `listar(limite=100)` exibido na home com auto-atualização 30s

3. **Exportação consolidada** (`analise/exportacao_consolidada.py`)
   - Dashboard + Excel + PDF auditoria + análise CSV em ZIP único
   - Card especial (gradiente azul) na página Análise

4. **Indicadores na home** (`web_painel/index.html`)
   - 4 cards: Pacientes BPA na RAM, Atendimentos na RAM, Backups, Status BPA

5. **Lembrete de competência**
   - Banner vermelho se BPA do mês não exportado, verde se sim

6. **Modo escuro**
   - CSS variables dark mode, toggle com localStorage

### Arquivos
- `integracao/backup_utils.py` (novo)
- `auditoria_log.py` (novo)
- `analise/exportacao_consolidada.py` (novo)
- `app_painel.py` (+129 linhas, seções 7-9)
- `web_painel/index.html` (reescrito)
- `web_painel/style.css` (+ dark mode)
- `web_painel/analise.html` (+ card exportação)

---

## Sessão 9 — 2026-05-15 — Remove BPA + card Atendimentos + paginação server-side

### Banner e card BPA removidos
- Banner vermelho/verde de lembrete de exportação removido do index.html
- Card indicador de BPA removido (também mandado embora a pedido)
- `dashboard_indicadores()` simplificado em app_painel.py

### Card Atendimentos (RAM) removido
- Usuário apontou que hospital.db não reflete em tempo real a recepção
- Agora só 2 cards: Pacientes BPA (RAM) e Backups Disponíveis

### Paginação server-side na consulta
- `consulta_recepcao.py`: nova `consultar_atendimentos_paginado()` retorna dict com `atendimentos` (100 registros), `total`, `pagina`, `total_paginas`
- `app_painel.py`: Eel expose `consulta_listar_atendimentos` agora aceita `pagina` param
- `consulta.html`: `mudarPagina()` chama servidor (nova função `consultar(pagina)`). Cada troca de página faz uma chamada Eel nova
- Resolve o timeout de 60s — antes enviava 30k+ registros pelo Eel, agora só 100 por vez
