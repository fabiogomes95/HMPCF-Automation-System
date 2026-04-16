
# 🏥 Gestão-BPA-Digital

## Ecossistema Hospitalar H.M.P.C.F
<p align="center">
  <img src="https://img.shields.io/badge/status-production-success?style=for-the-badge">
</p>

<p align="center">
  <b>Core & Backend</b><br>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/framework-flask-black?style=for-the-badge&logo=flask">
  <img src="https://img.shields.io/badge/database-sqlite-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
</p>

<p align="center">
  <b>Dados & Automação</b><br>
  <img src="https://img.shields.io/badge/RPA-PyAutoGUI-red?style=for-the-badge">
  <img src="https://img.shields.io/badge/cloud-Google_Sheets-34A853?style=for-the-badge&logo=googlesheets&logoColor=white">
  <img src="https://img.shields.io/badge/data--science-pandas-150458?style=for-the-badge&logo=pandas&logoColor=white">
</p>

<p align="center">
  <b>Front-end (Recepção)</b><br>
  <img src="https://img.shields.io/badge/html-5-E34F26?style=for-the-badge&logo=html5&logoColor=white">
  <img src="https://img.shields.io/badge/css-3-1572B6?style=for-the-badge&logo=css3&logoColor=white">
  <img src="https://img.shields.io/badge/javascript-ES6-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black">
</p>
Este ecossistema foi desenvolvido para modernizar e automatizar o fluxo completo de dados do **Hospital Municipal Presidente Café Filho**. O projeto resolve o gargalo entre a recepção física e o faturamento governamental, transformando processos manuais em uma operação totalmente otimizada e digital

----------

## 🚀 Impacto e Produtividade


A integração entre a **Recepção Automatizada** e o **Robô RPA** trouxe resultados imediatos e mensuráveis:

-   **⏳ Cenário Anterior:** Recepção baseada em fichas de papel e digitação manual lenta (24h para processar 1 dia).
    
-   **⚡ Cenário Atual:** Cadastro digital inteligente e processamento de **4 dias de produção por turno/máquina**.
    
-   **📈 Capacidade Total:** Entrega de **8 dias de produção por dia útil**, eliminando meses de backlog acumulado em tempo recorde.
    
-   **🏆 Ganho Real:** **+400% de velocidade operacional** com erro humano zero na entrada de dados.

----------

## 🛠️ Tecnologias Utilizadas

Stack moderna e robusta, com foco em **RPA e Ciência de Dados**:

-   💻 **Linguagem Core:** Python
-   🌐 **Web Framework:** Flask (interface e servidor local)
-   🗄️ **Banco de Dados:** SQLite (`hospital.db`)
-   🤖 **Automação RPA:** PyAutoGUI (simulação humana no BPA)
-   📊 **Ciência de Dados & BI:** Pandas + Matplotlib
-   ☁️ **Integração Cloud:** Google Drive API

----------

## ⚙️ Funcionalidades


### 1. 🧠 Recepção e Triagem Digital (Automação de Entrada)

A recepção atua como um **filtro inteligente** (Gatekeeper) para garantir a saúde dos dados:

-   **Validação Matemática:** Algoritmos de Módulo 11 validam CNS (Cartão SUS) e CPF no ato da digitação, bloqueando erros antes que cheguem ao faturamento.
    
-   **Prevenção de Duplicidade:** Monitoramento em tempo real para evitar protocolos repetidos no mesmo minuto/atendimento.
    
-   **Regra da Madrugada:** Lógica de negócio que atribui atendimentos noturnos (00h-07h) automaticamente ao plantão correto do dia anterior.
    
-   **Motor de Impressão Profissional:** Geração instantânea de boletins A4 via CSS `@media print`, eliminando o preenchimento manual de formulários.
    
-   **Cálculo Pediátrico Automático:** Conversão instantânea de idade para dias ou meses, garantindo precisão em atendimentos de recém-nascidos.
    

### 2. ☁️ "Gari da Nuvem" (Sincronização Invisível)

-   **Multithreading:** O sistema utiliza processamento em segundo plano para enviar dados ao Google Sheets sem travar a interface da recepção.
    
-   **Auditoria Remota:** Permite que a diretoria acompanhe os números da produção em tempo real, de qualquer lugar.
    

### 3. 🤖 Automação Robótica (RPA - Saída)

-   **Executor RPA:** Lê os dados sanitizados do banco e simula a digitação humana no sistema BPA com velocidade e precisão sobre-humana.
    
-   **Gestão de Lotes:** Organiza automaticamente a produção em blocos de até 99 registros, respeitando os limites técnicos do software governamental.
    

### 4. 📊 Inteligência de Negócio (BI)

-   **Dashboards de Demanda:** Mapas de calor que identificam horários de pico e bairros com maior volume de atendimentos.
    
-   **Relatórios Administrativos:** Exportação de planilhas Excel formatadas com separação automática de plantões diurnos e noturnos.

----------

## 📂 Arquitetura do Sistema

📦HMPCF-Automation-System
 ┣ 📂 analise      # Business Intelligence: Dashboards e relatórios automáticos.
 ┣ 📂 automacao    # Módulo RPA: O "robô" digitador e sua fila de dados (.csv).
 ┣ 📂 faturamento  # Integração: Conversores para .TXT (SUS) e sincronizadores.
 ┣ 📂 static       # Assets: Estilos CSS (Layout A4) e scripts Front-end.
 ┣ 📂 templates    # View: Interface Web da Recepção em HTML/Jinja2.
 ┣ 📜 app.py       # Core: Servidor central e o motor do "Gari da Nuvem".
 ┣ 📜 utils.py     # Cérebro: Motor de validações matemáticas e limpeza de dados.
 ┗ 📜 hospital.db  # Persistência: Banco de dados local SQLite.

----------

## 🚀 Instalação e Execução

### 🧪 Ambiente Virtual
``` text
python -m venv venv  
source venv/bin/activate # Linux/CachyOS
```
### 📦 Dependências
```text
pip install -r requirements.txt
```
### ⚙️ Configuração

-   Adicione o arquivo `credentials.json` (Google Cloud) na raiz do projeto

### ▶️ Execução
```text 
# Servidor  
python app.py  

# Robô RPA  
python automacao/executor_rpa.py  
  
# Relatórios  
python analise/dashboard_visual.py //segue o mesmo padrão em todos os outros relatórios 
  ```
----------
## 👨‍💻 Desenvolvedor

**Fábio Gomes da Silva**  
Desenvolvido em parceria com IA (NotebookLM)

-   🎓 Estudante de Análise e Desenvolvimento de Sistemas (Senac EAD)
-   🏥 Departamento de TI – Hospital M. Pres. Café Filho
