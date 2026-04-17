import os
import sys
import re

# Adiciona o caminho para importar o seu utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from utils import valida_cns
except ImportError:
    # Caso o utils esteja na mesma pasta
    from utils import valida_cns

print("==================================================")
print("🎯 AUDITORIA BPA: POSIÇÃO 53 + VALIDAÇÃO CNS")
print("==================================================\n")

arquivo = "ExpPaciente.txt"

if not os.path.exists(arquivo):
    print(f"❌ Arquivo '{arquivo}' não encontrado.")
    exit()

# Configuração baseada no layout fixo identificado
POSICAO_SEXO = 53 

sus_para_corrigir = []
total_lidos = 0
invalidos_matematicamente = 0

with open(arquivo, 'r', encoding='latin-1', errors='ignore') as f:
    for linha in f:
        # Verifica se a linha tem o tamanho mínimo e começa com número
        if len(linha) > POSICAO_SEXO and re.match(r'\d{15}', linha):
            total_lidos += 1
            sus = linha[:15].strip()
            sexo = linha[POSICAO_SEXO].upper()
            
            # Passo 1: Validação Matemática do CNS (via utils.py)
            if not valida_cns(sus):
                invalidos_matematicamente += 1
                continue # Pula para o próximo, nem olha o sexo

            # Passo 2: Validação do Sexo (Se não for M, F ou I, precisa de correção)
            if sexo not in ['M', 'F', 'I']:
                sus_para_corrigir.append(sus)

# Remove duplicados
sus_para_corrigir = list(set(sus_para_corrigir))

print("==================================================")
print(f"📊 Total de pacientes analisados: {total_lidos}")
print(f"🚫 SUS descartados por erro matemático: {invalidos_matematicamente}")
print(f"🚨 SUS válidos que precisam de correção de sexo: {len(sus_para_corrigir)}")
print("==================================================")

if sus_para_corrigir:
    with open("lista_correcao.txt", "w", encoding='utf-8') as out:
        for s in sus_para_corrigir:
            out.write(s + "\n")
    print(f"\n✅ Lista 'lista_correcao.txt' gerada com sucesso!")
    print(f"👉 Agora o Injetor TXT vai rodar apenas com números que o BPA aceita.")
else:
    print("\n🎉 Nenhum erro encontrado ou todos os erros eram de SUS matematicamente inválidos.")