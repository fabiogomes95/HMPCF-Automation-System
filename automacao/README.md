# 🤖 Módulo de Automação e Digitação (RPA)

Este diretório contém os scripts responsáveis pela "Automação de Saída" do Ecossistema H.M.P.C.F. O módulo foi desenhado para eliminar a digitação manual, unindo uma interface ágil de separação de lotes a um robô de digitação de alta velocidade.

## ⚙️ Scripts e Funcionalidades

### 1. `digitacao.py` (Assistente Visual BPA)
* **Objetivo:** Interface gráfica (GUI) rápida e ergonômica para selecionar os pacientes do dia e montar o lote de produção de faturamento.
* **Como funciona:** Carrega a base inteira do BPA (`ExpPaciente.txt`) na memória RAM, permitindo buscas instantâneas por Nome, CPF ou Cartão SUS (Data Mapping).
* **Destaques Operacionais:**
  * Organização automática de múltiplos médicos/enfermeiros em um único arquivo de saída (`PRODUCAO_data.txt`).
  * Foco total na ergonomia: o programa pode ser operado 100% pelo teclado (utilizando setas, TAB e Enter) para agilizar ao máximo a montagem do lote.

### 2. `executor_rpa.py` (O Robô de Digitação)
* **Objetivo:** Assumir o controle do mouse/teclado e injetar os dados diretamente no software oficial governamental do BPA.
* **Blindagem e Travas de Segurança (Filtro Triplo):** Antes de digitar qualquer coisa, o robô atua como um inspetor severo. Ele verifica:
  1. *Matemática:* Valida se o CNS atende à regra do Módulo 11 (via `utils.py`).
  2. *Cruzamento de Dados:* Só permite a digitação se o paciente realmente existir dentro da base `ExpPaciente.txt`.
  3. *Sanidade de Data:* Bloqueia datas corrompidas, idades no futuro ou nascimentos anteriores a 1900.
* **Gestão de Lotes de Produção:** O robô fatia automaticamente listas gigantes em blocos limitados a **99 pacientes**, respeitando a limitação técnica de cada "folha" dentro do sistema BPA.
* **Log de Auditoria:** Pacientes reprovados nas travas de segurança geram um log detalhado apontando a linha e o motivo da falha no arquivo `historico_rejeitados.txt` para inserir manualmente no BPA.

## 🛠️ Tecnologias e Bibliotecas Utilizadas
* **PyAutoGUI:** Motor principal de RPA, responsável por simular cliques e teclas e gerenciar as pausas estratégicas.
* **Tkinter:** Utilizado para a criação da interface gráfica intuitiva do `digitacao.py`.
* **Expressões Regulares (Regex):** Aplicadas para a extração cirúrgica de números de Cartão SUS e CPFs, driblando qualquer "sujeira" nos textos brutos.

## 🚀 Como Utilizar a Automação
1. Utilize o `digitacao.py` ou a sua planilha gerada para criar sua lista/lote de pacientes do dia.
2. Execute o `executor_rpa.py` e digite os parâmetros no terminal (data, médico ou enfermeiro).
3. Abra o sistema BPA em uma folha em branco, preencha o cabeçalho e confirme o início pressionando `Enter` na tela do robô.
4. Após o *delay* de 5 segundos, tire as mãos do computador. O robô vai começar a preencher e salvar as fichas em lotes.
⚠️ **Mecanismo de Defesa (Fail-Safe):** Caso você precise interromper a digitação do robô no meio do processo, mova o cursor do mouse rapidamente para qualquer um dos 4 cantos extremos do seu monitor.

---
*Módulo de Análise desenvolvido por **Fábio Gomes da Silva** em parceria com a IA (NotebookLM / Gemini) para o Hospital Municipal Presidente Café Filho.*