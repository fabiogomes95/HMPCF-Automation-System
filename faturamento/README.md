# ⚙️ Módulo BPA - Inteligência e Exportação de Dados

Este módulo é o centro de processamento de dados do **Hospital M. Pres. Café Filho**, responsável por garantir que as informações dos pacientes estejam limpas, validadas e prontas para o faturamento do SUS.

## 📂 Estrutura da Pasta

A pasta foi simplificada para conter apenas os dois scripts essenciais para a operação diária e o fechamento mensal:

### 1. `conciliar_manual_bpa.py` (O Faxineiro e Auditor)
Este é o script de **Sincronização e Auditoria**. Ele deve ser usado sempre que houver novas planilhas manuais vindas da recepção.
* **O que faz:** Lê planilhas em formato CSV e sincroniza os dados com o banco de dados `hospital.db`.
* **Inteligência:** Identifica automaticamente o nome, CPF e SUS, ignorando pontos, traços e espaços para evitar duplicidade.
* **Segurança:** Utiliza a lógica `INSERT OR REPLACE`, garantindo que CPFs repetidos não travem o sistema e que a informação mais recente seja preservada.
* **Relatórios:** Gera dois arquivos de log: `PROCESSADOS_...txt` (sucessos) e `ERROS_SINCRONIZACAO_...txt` (pacientes com dados inválidos que precisam de correção).

### 2. `exportar_bpa.py` (O Gerador de Faturamento)
Este é o motor de **Exportação Definitiva**. Ele é utilizado para gerar o arquivo que será enviado ao sistema do Ministério da Saúde.
* **O que faz:** Extrai os dados validados diretamente do banco de dados SQLite e os converte para o formato `.txt` posicional.
* **Validação:** Executa um algoritmo de Módulo 11 para testar o CNS de cada paciente antes da exportação.
* **Engenharia Posicional:** Monta as linhas de texto seguindo o layout exato exigido pelo sistema BPA (campos com tamanhos fixos).

---

## 🔄 Fluxo de Trabalho Sugerido

1.  **Sincronização:** Assim que receber a planilha da recepção, execute o `conciliar_manual_bpa.py`.
2.  **Auditoria:** Abra o arquivo de erros gerado. Se houver pacientes lá, corrija-os na planilha original e rode o sincronizador novamente.
3.  **Fechamento:** Com o banco de dados atualizado e sem erros pendentes, execute o `exportar_bpa.py` para gerar o arquivo final de faturamento.

---

## 🚀 Como Executar

```bash
# Para sincronizar e auditar planilhas:
python conciliar_manual_bpa.py

# Para gerar o arquivo .txt de faturamento:
python exportar_bpa.py