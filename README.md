<<<<<<< HEAD
# 🏥 Sistema de Boletim de Atendimento (H.M.P.C.F)

Este projeto visa a modernização e digitalização da interface do **Boletim de Atendimento** do Hospital M. Pres. Café Filho. 

Nesta fase atual, o repositório contém a construção da **Interface de Usuário (Front-end)**, desenhada para ser preenchida digitalmente com máxima agilidade e impressa com perfeição, substituindo os antigos formulários de papel por uma aplicação Web inteligente.

---

## 🚀 Funcionalidades da Interface

- **Layout Fiel ao Físico:** Interface A4 projetada na tela para familiaridade imediata dos recepcionistas e equipe médica.
- **Engenharia de Impressão (`@media print`):** Regras de CSS dedicadas que garantem uma impressão limpa (removendo botões, menus e margens do navegador), forçando a exibição de linhas pautadas simuladas e economizando tinta nas áreas desnecessárias.
- **Design Responsivo e Fluido:** Utilização de Flexbox e CSS Grid para alinhamento perfeito de caixas, tabelas de sinais vitais e blocos de anotações.
- **Preparação para Lógica Dinâmica:** Estrutura de botões de procedência e prioridades de atendimento (prontos para receberem o JavaScript).

---

## 📂 Estrutura Atual do Projeto

Neste momento, o projeto é composto estritamente pelos arquivos de Front-end:

```text
📦 Gestao-BPA-Digital
 ┣ 📂 analise_dados        # Processamento e visualização de estatísticas
 ┃ ┣ 📜 graficos.py        # Geração de dashboards com Seaborn/Matplotlib
 ┃ ┣ 📜 relatorio_mensal.py # Lógica de exportação e consolidação mensal
 ┃ ┗ 📜 dashboard_04_2026.png # Output visual dos dados
 ┣ 📂 bpa                  # Regras de negócio do Boletim de Produção Ambulatorial
 ┃ ┣ 📜 dados_bpa.csv      # Dados estruturados para migração
 ┃ ┗ 📜 migracao_bpa.py    # Script de tratamento e carga de dados
 ┣ 📂 static               # Arquivos estáticos (Estilo e Comportamento)
 ┃ ┣ 📜 style.css          # Estilos modulares e regras de impressão Web
 ┃ ┣ 📜 script.js          # Lógica do front-end e interações
 ┃ ┗ 📜 logo.png           # Logomarca oficial para documentos
 ┣ 📂 templates            # Telas do sistema (Flask/Jinja2)
 ┃ ┗ 📜 index.html         # Interface principal do Boletim Digital
 ┣ 📜 app.py               # Servidor Flask e rotas principais
 ┣ 📜 hospital.db          # Banco de dados SQLite (Produção)
 ┣ 📜 planilha.bat         # Gerador da planilha diaria/mensal dos atendimentos
 ┣ 📜 README.md            # Documentação do projeto
 ┣ 📜 requirements.txt     # Dependências do projeto (Python)
 ┗ 📜 start.vbs            # Script de inicialização rápida no Windows
```
--------------------------------------------------------------------------------
## 🛠️ Tecnologias Utilizadas (Até o momento)

![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)

* **HTML5:** Estruturação e Esqueleto semântico.
* **CSS3:** Estilização, Flexbox, Grid e regras de Print Web (`@media print`).
* **JavaScript:** Lógica de interface, tempo dinâmico e validações (Em andamento).
--------------------------------------------------------------------------------
## 👨‍💻 Desenvolvimento & IA
👨‍💻 Desenvolvido por **Fábio Gomes da Silva** em parceria com a IA **NotebookLM**

## 🤖 Assistência de IA (Pair Programming)
O front-end deste projeto (HTML, CSS e JavaScript) foi construído, refatorado e documentado em uma parceria direta com o NotebookLM. A inteligência artificial foi utilizada como uma ferramenta de pair programming e mentoria didática, auxiliando nos seguintes pontos:

- Separação de responsabilidades e aplicação de Clean Code.

- Construção de interfaces dinâmicas utilizando CSS Flexbox e Grid.

- Comunicação direta com drivers de Impressão Web (@media print e @page).

- Criação de guias didáticos e comentários explicativos em todo o código-fonte.

## 🚧 Fase Atual do Projeto
Atualmente, o desenvolvimento encontra-se focado no "Cérebro" da Interface (JavaScript):
- ✅ **HTML5**: Esqueleto semântico finalizado, blindado e estruturado.
- ✅ **CSS3**: Estilização modularizada e regras de comunicação com a impressora 100% concluídas.
- ⏳ **JavaScript** (Em andamento): Iniciando a construção das funções de tempo automático (relógio inteligente que pausa durante a digitação) e, em seguida, as validações matemáticas de documentos (CPF/CNS).

## 🔮 Futuro
Este projeto está sendo desenhado para se tornar uma aplicação completa para o Hospital, otimizando o fluxo de atendimento e os dados gerados para o BPA. No futuro, o sistema evoluirá para uma arquitetura modular integrando: 
- **Backend: Python 🐍 / Flask 🌶️** (o centro de tudo, processo das informações, cálculos etc.)
- **Banco de Dados: SQLite3 🗄️** (Banco de dados escolhido para armazenamento de dados (*ainda pode ser alterado*)
- **Ciência de Dados (Estatísticas e Dashboards)** - **Pandas 🐼 Seaborn 📊 Matplotlib 📈** 
(Análise, extração e limpeza de dado)
=======

# 🏥 Gestão-BPA-Digital

## Ecossistema Hospitalar H.M.P.C.F


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
>>>>>>> master
