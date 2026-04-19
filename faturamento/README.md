# 💰 Módulo de Faturamento e Integração BPA

Este diretório contém os scripts responsáveis pela etapa final do Ecossistema H.M.P.C.F: a comunicação com o Ministério da Saúde. 

Eles pegam todos os atendimentos salvos, aplicam rigorosas regras de validação (para evitar rejeição e perda de receita) e geram lotes, planilhas e arquivos posicionais prontos para envio ao Governo.

## ⚙️ Scripts e Funcionalidades

### 1. `gerador_arquivo_bpa.py` (O Motor de Exportação)
* **Objetivo:** Puxar os cadastros do banco local e transformá-los no exato arquivo `TXT` que o software governamental do BPA exige.
* **Como funciona:** Varre o banco de dados (por mês ou geral) e formata os dados em um **Layout Posicional** rigoroso (ex: o Nome sempre tem 30 caracteres preenchidos com espaços; o Sexo sempre na mesma posição).
* **Prevenção de Glosa:** Durante a exportação, aplica a trava de validação do Cartão SUS. Se o SUS for falso, o paciente não entra no arquivo final e o sistema gera um `log_erros.txt` para aviso à gestão.

### 2. `importador_recepcao.py` (O Importador Inteligente em Lote)
* **Objetivo:** Processar e centralizar lotes de arquivos `.csv` gerados diariamente pela recepção.
* **Smart Update (Atualização Cirúrgica):** Ele não apenas insere pacientes novos. Se o paciente já existir no banco, ele lê campo a campo. Se o banco estiver sem CPF, mas a recepção conseguiu o CPF hoje, o script atualiza apenas esse campo, enriquecendo o banco de dados sem apagar o histórico.

### 3. `sincronizar_contingencia.py` (O Salva-Vidas de Planilhas Manuais)
* **Objetivo:** Sincronizar dados quando a recepção trabalha offline ou anota em planilhas secundárias.
* **Como funciona:** Utiliza *Expressões Regulares (Regex)* como "caçadores de dados". O script procura onde está o nome, o CPF e o SUS independentemente da coluna em que a recepcionista digitou, limpando toda a sujeira de formatação.
* **Auditoria:** Gera dois relatórios físicos no final: `PROCESSADOS` (quem deu certo) e `ERROS` (quem ficou de fora e o motivo exato).

## 🛠️ Tecnologias Utilizadas
* **Tkinter:** Criação de janelas flutuantes e exploradores de arquivos para uso simplificado pela equipe administrativa.
* **SQLite3:** Leitura em massa dos dados utilizando a cláusula `JOIN` para unir os atendimentos ao cadastro.
* **Regex (re):** Algoritmos de caça a padrões para identificar CPFs e Cartões SUS perdidos no meio de textos sujos.

## 🚀 Como Utilizar
1. Execute o script desejado com dois cliques ou pelo terminal.
2. Interaja com a janela suspensa (Pop-up) para escolher o mês desejado ou a planilha de entrada.
3. Aguarde o processamento. Os arquivos de saída e os relatórios de erros serão salvos automaticamente na mesma pasta de origem.

---
*Desenvolvido por **Fábio Gomes da Silva** em parceria com a IA (NotebookLM / Gemini) para o Hospital Municipal Presidente Café Filho.*