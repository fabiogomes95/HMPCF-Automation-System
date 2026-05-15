# 🏥 HMPCF-Automation-System — Ecossistema Hospitalar H.M.P.C.F

Sistema completo de automação hospitalar desenvolvido para modernizar o fluxo de dados do **Hospital Municipal Presidente Café Filho** (Extremoz/RN). Substitui fichas de papel por um fluxo digital integrado com **RPA**, **Business Intelligence** e **sincronização em nuvem**, resolvendo o gargalo entre a recepção física e o faturamento governamental (SUS/BPA).

---

## 📈 Impacto Operacional

| Indicador | Antes | Agora |
|-----------|-------|-------|
| Processamento | 24h para 1 dia de produção | 4 dias de produção por turno/máquina |
| Capacidade | Backlog crescente | 8 dias de produção por dia útil |
| Velocidade | — | **+400%** com margem de erro zero |

---

## 🧱 Arquitetura

```
📦 HMPCF-Automation-System
 ┣ 📂 analise/          # BI — Dashboards, relatórios Excel e PDF
 ┣ 📂 automacao/        # RPA — Robô digitador, triagem e fila de lotes
 ┣ 📂 integracao/       # Integração SUS — conversores TXT e sincronizadores
 ┣ 📂 web_recepcao/     # Frontend da Recepção (Eel)
 ┣ 📂 web_painel/       # Frontend do Painel de Gestão (Eel)
 ┣ 📂 scripts/          # Ferramentas de manutenção DBA
 ┣ 📂 assets/           # Recursos estáticos (ícones)
 ┣ 📜 app_recepcao.py   # Servidor da Recepção (Eel, porta 8000)
 ┣ 📜 app_painel.py     # Servidor do Painel de Gestão (Eel, porta 8001)
 ┣ 📜 planilha_nuvem.py # "Gari da Nuvem" — sincronizador Google Sheets
 ┣ 📜 utils.py          # Motor de validações (CPF, CNS, regex)
 ┣ 📜 corrigir_data.py  # Correção de datas impossíveis no Firebird
 ┣ 📜 hospital.db       # Banco SQLite local
 ┣ 📜 credentials.json  # Chave de API Google Cloud
 ┗ 📜 requirements.txt  # Dependências
```

---

## ⚙️ Módulos

### 🏪 Recepção (`app_recepcao.py` + `web_recepcao/`)
Formulário web A4 com cadastro inteligente de pacientes, busca automática por CPF/SUS, classificação de risco, sinais vitais, comorbidades e impressão do boletim. Atalho F2 para salvar. Validação matemática de CPF e SUS em tempo real no frontend.

### 🚀 Launcher Unificado (`main.py`)
Ponto de entrada único que:
1. **Verifica atualizações** no GitHub (compara `version.json` local × remoto)
2. Se há versão nova, pergunta se deseja atualizar (via `git pull` ou download ZIP)
3. Inicia os servidores da **Recepção** (8000) e **Painel** (8001) em simultâneo
4. Abre o navegador automaticamente

```
python main.py                  # Modo normal (com verificação de update)
python main.py --no-update      # Pula verificação
python main.py --build          # Testa se PyInstaller está pronto
```

### 📊 Painel de Gestão (`app_painel.py` + `web_painel/`)
Central de controle com 4 módulos:
- **Digitação** — busca pacientes na base BPA (Firebird em RAM), monta lotes de 99 com quebra automática
- **Triagem** — extrai CPF/SUS de dados sujos, divide em lotes por enfermeiro
- **Robô RPA** — executa digitação automática no sistema BPA governamental com PyAutoGUI
- **Análise / BI** — dashboards, relatórios Excel e PDFs de auditoria via interface web

### ☁️ Gari da Nuvem (`planilha_nuvem.py`)
Thread em background sincroniza atendimentos do SQLite para uma planilha Google Sheets em tempo real, respeitando a regra de plantão (07h).

### 🤖 Automação / RPA (`automacao/`)
- **`executor_rpa.py`** — robô digitador com validação tripla e fail-safe (mouse no canto para parar)
- **`digitacao.py`** — assistente de digitação manual com montagem de lotes
- **`cpf_sus.py`** — extrator/validador de CPF e SUS via regex + Módulo 11

### 🔌 Integração SUS (`integracao/`)
Acessível via web no Painel de Gestão → [Integração](http://localhost:8001/integracao.html)
- `gerador_arquivo_bpa.py` — exporta SQLite → TXT posicional Datasus
- `gerador_csv.py` — converte CSVs antigos para TXT BPA
- `banco_de_dados_hospital_bpa.py` — sincronizador SQLite ↔ Firebird
- `importador_recepcao.py` — importa CSV com Smart Update (enriquece campos vazios)
- `sincronizar_contingencia.py` — processa planilhas offline com regex inteligente
- `nacionalidade_gdb.py` — aniquila NULLs no Firebird
- `duplicatas_gdb.py` — caça e remove duplicatas por pontuação

### 📈 Business Intelligence (`analise/`)
Acessível via web no Painel de Gestão → [Análise / BI](http://localhost:8001/analise.html)
- `dashboard_visual.py` — dashboard PNG (idade x sexo, top bairros, picos, volume)
- `planilha_producao.py` — relatório Excel com separação DIURNO/NOTURNO e regra da madrugada
- `auditoria_periodica.py` — PDF de auditoria mensal/trimestral/semestral (WeasyPrint)
- `analise_anual_csv.py` — relatório Top 20 a partir de CSVs
- `historico_paciente.py` — "Lupa do Auditor" — busca interativa por nome/CPF/SUS

### 🛠️ Manutenção / DBA (`scripts/`)
- `faxina.py` — faxina geral do banco SQLite (valida CPF/SUS, mescla duplicados, recria estrutura)
- `cns_validator_tool.py` — faxina cirúrgica de CNS inválidos
- `fusao.py` — deduplicação inteligente com fusão de clones
- `auditor_bpa.py` — auditor de sexo em TXT BPA
- `corrigir_sexo_bpa.py` — RPA corretor de sexo no sistema BPA
- `att_sexo.py` — atualização em massa de sexo no SQLite
- `sonda_db.py` — debug de registros no banco
- `cpf_bpa.py` — sincronizador alternativo por nome + data de nascimento
- `gerar_txt_fusao.py` — relatório pós-faxina

---

## 🛠️ Tecnologias

<p align="left">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  <img src="https://img.shields.io/badge/eel-2E8B57?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white" />
  <img src="https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white" />
  <img src="https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E" />
  <img src="https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white" />
  <img src="https://img.shields.io/badge/firebird-CC2927?style=for-the-badge&logo=firebird&logoColor=white" />
  <img src="https://img.shields.io/badge/Google%20Sheets-34A853?style=for-the-badge&logo=googlesheets&logoColor=white" />
</p>

- **Backend:** Python 3.11+, Eel (Desktop WebView), Firebird SQL
- **Frontend:** HTML5, CSS3 (`@media print`), JavaScript ES6+, Bootstrap 5
- **RPA:** PyAutoGUI
- **BI:** Pandas, Matplotlib, Seaborn, OpenPyXL, WeasyPrint
- **Cloud:** Google Sheets & Drive API (gspread, google-auth)
- **Banco:** SQLite3, Firebird (BPAMAG.GDB)

---

## 🚀 Instalação

```bash
git clone https://github.com/fabiogomes95/HMPCF-Automation-System.git
cd HMPCF-Automation-System
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### ⚙️ Configuração Google Sheets
Coloque o arquivo `credentials.json` (Google Cloud Console) na raiz do projeto para ativar o Gari da Nuvem.

### ▶️ Execução

| Módulo | Comando | Porta |
|--------|---------|-------|
| Launcher (recomendado) | `python main.py` | 8000 + 8001 |
| Recepção | `python app_recepcao.py` | 8000 |
| Painel de Gestão | `python app_painel.py` | 8001 |
| Gari da Nuvem | Inicia automaticamente com a Recepção | — |

**Produção (Windows):** execute `start_painel.vbs` (Painel) ou `start_recepcao.vbs` (Recepção).

### 🏗️ Execução via atalho no Windows

Crie atalhos na Área de Trabalho apontando para:
- `wscript.exe "C:\caminho\HMPCF-Automation-System\start_painel.vbs"` — Painel
- `wscript.exe "C:\caminho\HMPCF-Automation-System\start_recepcao.vbs"` — Recepção

---

## 📌 Fluxo de Trabalho

1. **Recepção** cadastra pacientes no formulário web → SQLite
2. **Gari da Nuvem** sincroniza com Google Sheets em background
3. **Painel de Gestão** carrega base BPA do Firebird
4. **Digitação/Triagem** prepara lotes de 99 pacientes
5. **Robô RPA** digita automaticamente no sistema governamental
6. **Integração** exporta para TXT Datasus / sincroniza sistemas
7. **BI** gera dashboards, relatórios Excel e PDFs de auditoria

---

Desenvolvido por **Fábio Gomes da Silva** • <fabiogsilva@disroot.org>
