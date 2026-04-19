# 🏥 HMPCF-Automation-System (Ecossistema Hospitalar H.M.P.C.F)

> Este ecossistema foi desenvolvido para modernizar e automatizar o fluxo completo de dados do **Hospital Municipal Presidente Café Filho**. O projeto resolve o gargalo histórico entre a recepção física e o faturamento governamental, transformando processos manuais em uma operação totalmente otimizada, digital e à prova de falhas.

---

## 🚀 Impacto e Produtividade

A integração entre a **Recepção Automatizada**, o **Business Intelligence** e o **Robô RPA** trouxe resultados imediatos e mensuráveis para a instituição:

* ⏳ **Cenário Anterior:** Recepção baseada em fichas de papel e digitação manual lenta (24h para processar 1 dia de produção).
* ⚡ **Cenário Atual:** Cadastro digital inteligente e processamento de **4 dias de produção por turno/máquina**.
* 📈 **Capacidade Total:** Entrega de **8 dias de produção por dia útil**, eliminando meses de backlog acumulado em tempo recorde.
* 🏆 **Ganho Real:** **+400% de velocidade operacional** com margem de erro humano zero na entrada de faturamento.

---

## 🛠️ Tecnologias Utilizadas

Stack moderna, Full-Stack e robusta, com foco em **RPA (Robotic Process Automation)** e **Ciência de Dados**:

<p align="left">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
  <img src="https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3" />
  <img src="https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E" alt="JavaScript" />
  <img src="https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
  <img src="https://img.shields.io/badge/Google%20Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white" alt="Google Drive" />
</p>

* 💻 **Linguagem Core:** Python
* 🌐 **Web Framework (Backend):** Flask
* 🖥️ **Frontend:** HTML5, CSS3 (`@media print`) e Vanilla JavaScript (ES6+ assíncrono)
* 🗄️ **Banco de Dados:** SQLite3 (`hospital.db`) com consultas parametrizadas
* 🤖 **Automação RPA:** PyAutoGUI e Tkinter (Interfaces Gráficas e Simulação Humana)
* 📊 **Ciência de Dados & BI:** Pandas, Matplotlib, Seaborn e OpenPyXL
* ☁️ **Integração Cloud:** Google Drive & Sheets API (Multithreading)

---

## 📂 Arquitetura do Sistema e Módulos

O projeto foi estruturado seguindo rigorosos padrões de modularização de software. Cada pasta possui o seu próprio `README.md` detalhado. Abaixo, a árvore principal do ecossistema:

```text
📦 HMPCF-Automation-System
 ┣ 📂 analise       # Business Intelligence: Dashboards e relatórios automáticos.
 ┣ 📂 automacao     # Módulo RPA: O "robô" digitador e sua fila de dados (.csv).
 ┣ 📂 faturamento   # Integração: Conversores para .TXT (SUS) e sincronizadores.
 ┣ 📂 static        # Assets: Estilos CSS (Layout A4) e scripts Front-end.
 ┣ 📂 templates     # View: Interface Web da Recepção em HTML/Jinja2.
 ┣ 📜 app.py        # Core: Servidor central e o motor do "Gari da Nuvem".
 ┣ 📜 utils.py      # Cérebro: Motor de validações matemáticas e limpeza de dados.
 ┗ 📜 hospital.db   # Persistência: Banco de dados local SQLite.
```

* **`/ (Raiz)` - O Núcleo do Servidor:** Contém o `app.py` (motor do servidor e a fila em segundo plano "Gari da Nuvem"), o `utils.py` (canivete suíço com validações matemáticas via Regex e Módulo 11) e o `start.vbs` (lançador silencioso).
* **`/templates` e `/static` - Frontend Inteligente:** A interface de usuário. Converte o navegador numa folha A4 virtual para impressão e possui um cérebro em JavaScript que trava cliques duplos ("Efeito Metralhadora") e calcula idades pediátricas em tempo real.
* **`/automacao` - Módulo RPA (Saída):** Une uma interface gráfica rápida de montagem de lotes a um robô injetor. O robô aplica um "Filtro Triplo" de segurança antes de digitar os dados em altíssima velocidade no sistema BPA governamental.
* **`/faturamento` - Integração Oficial (SUS):** Scripts responsáveis por traduzir o banco de dados em Layout Posicional (TXT) do Datasus. Conta também com o "Smart Update" para sincronização de arquivos CSV legados e correção em contingência.
* **`/analise` - Business Intelligence (BI):** O Cientista de Dados do hospital. Gera dashboards visuais de mapas de calor, fluxo etário e picos de atendimento, além de exportar relatórios gerenciais em Excel respeitando a "Regra da Madrugada" dos plantões.
* **`/archive` - Caixa de Ferramentas (DBA):** Ferramentas de manutenção para limpar, auditar e corrigir registros do banco de dados (ex: exclusão em massa de CPFs corrompidos e injeção corretiva de dados no faturamento).

---

## 🚀 Instalação e Execução

### 🧪 1. Ambiente Virtual
Clone o repositório e crie um ambiente virtual isolado para evitar conflito de bibliotecas no seu sistema:

```bash
git clone [https://github.com/fabiogomes95/HMPCF-Automation-System.git](https://github.com/fabiogomes95/HMPCF-Automation-System.git)
cd HMPCF-Automation-System
python -m venv venv

# Ativar no Windows:
venv\Scripts\activate

# Ativar no Linux/Mac:
source venv/bin/activate
```

### 📦 2. Dependências

Com o ambiente ativado, instale as bibliotecas exigidas:
```bash
Bash
pip install -r requirements.txt
```

### ⚙️ 3. Configuração (Integração em Nuvem)

O sistema possui uma integração assíncrona com o Google Sheets ("Gari da Nuvem").
Para que funcione, coloque o seu arquivo de chave de API chamado credentials.json (gerado no Google Cloud Console) diretamente na pasta raiz do projeto.

### ▶️ 4. Execução
Para abrir a recepção inteligente, você tem duas opções:

Modo Desenvolvedor: Execute python app.py no terminal e acesse http://127.0.0.1:5000 no navegador.

Modo Produção (Windows): Dê dois cliques no arquivo start.vbs. Ele subirá o servidor de forma oculta e abrirá a janela do navegador automaticamente.

--------------------------------------------------------------------------------
Desenvolvido por **Fábio Gomes da Silva** em parceria com a IA **(NotebookLM / Gemini)** para o **Hospital Municipal Presidente Café Filho.**