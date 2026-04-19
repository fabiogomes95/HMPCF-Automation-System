# 🗄️ Arquivo Morto e Ferramentas de Manutenção (Archive)

Este diretório funciona como a "Caixa de Ferramentas" do Ecossistema H.M.P.C.F. Ele armazena scripts de manutenção, sondagem de banco de dados e robôs de correção criados para demandas pontuais. 

Embora não façam parte do fluxo de trabalho diário da recepção ou BPA, estes scripts são mantidos como um acervo valioso para auditorias futuras ou correções em massa de dados legados.

## 🛠️ Scripts e Ferramentas Disponíveis

### 1. `cns_validator_tool.py` (A Faxina Cirúrgica)
* **Objetivo:** Script de saneamento profundo do banco de dados (`hospital.db`).
* **Como funciona:** Varre todos os cadastros aplicando a validação matemática oficial do Ministério da Saúde. Pacientes com Cartão SUS falsos/inválidos são excluídos automaticamente (junto com suas fichas), e datas de nascimento quebradas são resetadas. Ignora propositalmente erros de CPF para focar apenas na integridade do SUS.
* **Saída:** Gera um relatório detalhado (`relatorio_faxina.txt`) com o log de tudo que foi alterado.

### 2. `auditor_bpa.py` (O Fiscal do TXT)
* **Objetivo:** Auditar os arquivos gerados para faturamento (`ExpPaciente.txt`).
* **Como funciona:** Lê o arquivo estruturado do BPA, checa a Posição 53 (onde fica o Sexo) e cruza isso com a validação matemática do CNS. Identifica rapidamente quais pacientes estão com o campo "sexo" em branco ou fora do padrão (M, F, I).
* **Saída:** Gera o arquivo `lista_correcao.txt` isolando apenas os pacientes que precisam de intervenção manual no sistema do governo.

### 3. `corrigir_sexo_bpa.py` (Robô Injetor de Correção)
* **Objetivo:** Automação RPA complementar.
* **Como funciona:** Lê a `lista_correcao.txt` gerada pelo Auditor. O robô assume o controle do teclado/mouse (via PyAutoGUI) e digita em alta velocidade os pacientes no sistema BPA apenas para forçar a letra 'I' (Indefinido) no campo sexo, utilizando dados e procedimentos de preenchimento rápido para salvar o cadastro corrigido.

### 4. `att_sexo.py` (Saneamento Rápido)
* **Objetivo:** Correção direta no SQLite.
* **Como funciona:** Varre o banco de dados e altera automaticamente para `I` todos os pacientes cujo campo de sexo esteja nulo, vazio ou preenchido com caracteres inválidos, garantindo compatibilidade com a exportação para o BPA.

### 5. `sonda_db.py` (O Rastreador)
* **Objetivo:** Ferramenta de diagnóstico de dados e *debug*.
* **Como funciona:** Permite fazer consultas flexíveis e super-rápidas direto no banco de dados, sem precisar abrir interface gráfica. Útil para verificar, por exemplo, se um paciente específico foi de fato salvo pelo sistema, quais os exatos caracteres salvos no sexo ou formatação de documentos.

---
⚠️ **ATENÇÃO:** *Como a maioria destes scripts atua diretamente fazendo comandos `DELETE` ou `UPDATE` no banco de dados ou movimentando o mouse pela tela, eles devem ser utilizados apenas pelo administrador do sistema.*

---
*Desenvolvido por **Fábio Gomes da Silva** em parceria com a IA (NotebookLM / Gemini) para o Hospital Municipal Presidente Café Filho.*