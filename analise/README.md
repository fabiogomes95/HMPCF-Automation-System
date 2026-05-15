# 📊 Módulo de Análise e Business Intelligence (BI)

Este diretório contém os scripts de inteligência de negócio do sistema HMPCF. Eles transformam os atendimentos salvos no banco SQLite em **relatórios gerenciais**, **gráficos visuais** e **PDFs de auditoria** — prontos para impressão ou envio à diretoria.

Todas as ferramentas funcionam **via terminal** (com parâmetros opcionais) e **via interface web** no Painel de Gestão (Eel, porta 8001 → [Análise / BI](http://localhost:8001/analise.html)).

---

## 📋 Scripts

### 1. `planilha_producao.py` — Relatório Excel por Plantão

Gera uma planilha `.xlsx` profissional com separação automática entre **Plantão DIURNO** (07h–18:59) e **NOTURNO** (19h–06:59).

**Regra da Madrugada:** atendimentos antes das 07h são contabilizados no plantão da noite anterior.

**Diferenciais:**
- Extermina duplicatas de "cliques acidentais" na recepção
- Cabeçalhos coloridos (azul para dia, vermelho para noite)
- Painel congelado para scroll sem perder o cabeçalho
- Mesclagem automática de células dos plantões

**Como usar (terminal):**
```bash
python planilha_producao.py
# Depois digite o mês desejado (ex: 04-2026)
```

**Via Eel (web):** `analise_gerar_relatorio_mes("04-2026")` — parâmetro `mes_ref` no modal.

---

### 2. `dashboard_visual.py` — Dashboard Gráfico PNG

Gera um painel visual com **4 gráficos** em alta resolução (300 DPI):

| Gráfico | Descrição |
|---------|-----------|
| Idade x Sexo | Histograma empilhado mostrando a distribuição etária por sexo |
| Top 10 Bairros | Os bairros com maior demanda de atendimentos |
| Picos de Horário | Volume de pacientes por hora do dia |
| Volume Diário | Atendimentos por dia ao longo do mês |

Também exibe no terminal o **Top 20 pacientes mais frequentes** com a linha do tempo de cada visita.

**Como usar (terminal):**
```bash
python dashboard_visual.py
```

**Via Eel (web):** `analise_gerar_dashboard()` — sem parâmetros.

---

### 3. `auditoria_periodica.py` — PDF de Auditoria

Gera um PDF otimizado para impressão (modo econômico de tinta) com os **20 pacientes mais frequentes** de um período.

**Períodos disponíveis:**
- Mensal (30 dias)
- Trimestral (90 dias)
- Semestral (180 dias)

**Layout:** duas colunas (side-by-side) para economizar papel, com linha do tempo individual de cada paciente.

**Como usar (terminal):**
```bash
python auditoria_periodica.py
# Escolha 1, 3 ou 6 no menu
```

**Via Eel (web):** `analise_gerar_auditoria_periodo("1")` — parâmetro `opcao` no modal.

---

### 4. `analise_anual_csv.py` — Relatório de Frequência CSV

Lê arquivos `.csv` antigos da recepção, cruza dados por CPF/SUS/Nome+DN para identificar pacientes únicos, e gera um PDF com o **Top 20 pacientes** independentemente do período.

Ideal para analisar **dados históricos** que ainda não foram importados para o SQLite.

**Como usar (terminal):**
```bash
python analise_anual_csv.py
# Coloque os CSVs na mesma pasta analise/
```

**Via Eel (web):** `analise_analisar_csvs_para_pdf()` — sem parâmetros.

---

### 5. `historico_paciente.py` — Lupa do Auditor

Ferramenta interativa de consulta rápida. Busca o histórico **completo** de atendimentos de um paciente por:

- **Nome** (busca parcial)
- **CPF** (com ou sem máscara)
- **Cartão SUS** (com ou sem máscara)

Exibe nome, CPF, SUS e a linha do tempo cronológica de cada atendimento com data, hora e procedência.

**Como usar (terminal):**
```bash
python historico_paciente.py
# Depois digite o nome, CPF ou SUS
```

**Via Eel (web):** `analise_buscar_historico("termo")` — parâmetro `termo` no modal.

---

## 🌐 Interface Web (Eel)

Todas as 5 ferramentas estão disponíveis no Painel de Gestão, página **Análise / BI**:

```
http://localhost:8001/analise.html
```

Cada card abre um modal com os parâmetros necessários (quando aplicável). O resultado é exibido no terminal de saída abaixo dos cards.

---

## 🛠️ Tecnologias

| Biblioteca | Para que serve |
|------------|----------------|
| **Pandas** | Manipulação, agrupamento e limpeza dos dados |
| **Matplotlib + Seaborn** | Geração dos gráficos do dashboard |
| **OpenPyXL** | Estilização e formatação do Excel |
| **WeasyPrint** | Renderização de HTML para PDF |
| **SQLite3** | Conexão direta com o banco hospital.db |
| **Eel** | Interface web (Painel de Gestão, porta 8001) |

---

## 📂 Arquivos de Saída

| Script | Arquivo Gerado |
|--------|---------------|
| `planilha_producao.py` | `Relatorio_Producao_HMPCF.xlsx` |
| `dashboard_visual.py` | `analise/dashboard_hmpcf.png` |
| `auditoria_periodica.py` | `analise/RELATORIO_AUDITORIA_*.pdf` |
| `analise_anual_csv.py` | `analise/RELATORIO_FREQUENCIA_CSV.pdf` |
| `historico_paciente.py` | Retorno em string (web) / terminal |

---

*Módulo de Análise desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*
