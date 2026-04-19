
# 📊 Módulo de Análise de Dados e Business Intelligence (BI)

Este diretório contém os scripts em Python responsáveis pelo módulo de Inteligência de Negócio do Ecossistema H.M.P.C.F. Eles leem os dados estruturados pelo sistema da recepção e os transformam em relatórios visuais e administrativos profissionais.

## ⚙️ Arquivos e Funcionalidades

### 1. `dashboard_visual.py` (Painel de Demanda)
Desenvolvido para analisar o banco SQLite e gerar gráficos analíticos exportados em alta resolução (`.png`).
* **Top 30 Pacientes Recorrentes:** Gera um relatório textual no terminal identificando os pacientes que mais retornaram à unidade no mês, incluindo a contagem e as horas exatas de cada visita.
* **Limpeza Automática de Dados:** Utiliza integração com o módulo central (`utils.py`) para higienizar categorias (ex: juntar o bairro "Centro" e "CENTRO" no mesmo cálculo) e filtrar inconsistências de idade.
* **Métricas Geradas (Seaborn/Matplotlib):**
  * **Perfil Etário:** Gráfico empilhado mostrando a idade dos pacientes separada por sexo.
  * **Mapa de Demanda:** Gráfico de barras revelando os Top 10 Bairros que mais geraram atendimentos.
  * **Picos de Horário:** Identificação visual das horas do dia com maior fluxo na recepção.
  * **Volume Diário:** Linha do tempo apontando a quantidade de pacientes por dia ao longo do mês.

### 2. `planilha_producao.py` (Relatório Administrativo)
Script responsável por exportar os atendimentos para planilhas do Excel (`.xlsx`), com as regras de gestão já embutidas.
* **O Exterminador de Clones:** Aplica uma trava com `drop_duplicates` que deleta automaticamente pacientes duplicados (Efeito Metralhadora) na mesma data e hora antes de gerar a planilha.
* **Inteligência Temporal (Regra da Madrugada):** Aplica a regra de negócio hospitalar onde atendimentos que ocorrem de madrugada (antes das 07:00h) são agrupados no plantão do dia anterior.
* **Separação de Turnos:** Divide automaticamente os blocos de produção entre Plantão **DIURNO** (07h às 18:59) e Plantão **NOTURNO** (19h às 06:59).
* **Estilização Automática (OpenPyXL):** A planilha exportada já nasce com design profissional, possuindo mesclagem de células, cabeçalhos com cores institucionais (azul para o dia, vermelho para a noite), fontes em negrito e painéis travados.

## 🛠️ Tecnologias e Bibliotecas Utilizadas
* **Pandas:** Para manipulação em massa, agrupamentos matemáticos e tratamento da base de dados.
* **Matplotlib & Seaborn:** Para a construção e renderização do painel gráfico.
* **OpenPyXL:** Para a estilização e automação na criação da estrutura das células do Excel.
* **SQLite3:** Conexão nativa com consultas em SQL utilizando `DISTINCT` para impedir o "Efeito Cartesiano" de duplicação de cadastros.

## 🚀 Como Utilizar
1. Execute o script desejado através do atalho ou pelo terminal (`python dashboard_visual.py` ou `python planilha_producao.py`).
2. O prompt solicitará que você digite o mês que deseja gerar (ex: `04/2026` ou `04-2026`).
3. O sistema varrerá o banco, organizará os lotes e exportará os arquivos `.png` ou `.xlsx` diretamente na mesma pasta, prontos para envio ou impressão.

---
*Módulo de Análise desenvolvido por **Fábio Gomes da Silva** em parceria com a IA (NotebookLM / Gemini) para o Hospital Municipal Presidente Café Filho.*
