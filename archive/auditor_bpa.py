# ==============================================================================
# AUDITOR DE DADOS GOVERNAMENTAIS (BPA)
# ==============================================================================
# OBJETIVO:
# Ler o arquivo TXT gigante gerado pelo sistema do Ministério da Saúde,
# analisar posições de caracteres fixos e descobrir quais pacientes 
# precisam de correção manual antes do faturamento ser fechado.
# ==============================================================================

import os
import sys
import re

# Sobe um nível de pasta para importar a trava de validação do arquivo utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils import valida_cns
except ImportError:
    from utils import valida_cns # Caso o script rode de outro local

print("==================================================")
print("🎯 AUDITORIA BPA: POSIÇÃO 53 + VALIDAÇÃO CNS")
print("==================================================\n")

arquivo = "ExpPaciente.txt"
if not os.path.exists(arquivo):
    print(f"❌ Arquivo '{arquivo}' não encontrado.")
    exit()

# ==============================================================================
# 1. MAPEAMENTO DE DADOS (DATA MAPPING)
# ==============================================================================
# No layout do Governo, o campo "Sexo" fica exatamente no caractere 53 da linha.
POSICAO_SEXO = 53 

sus_para_corrigir = []
total_lidos = 0
invalidos_matematicamente = 0

# ==============================================================================
# 2. VARREDURA DO ARQUIVO BRUTO E AUDITORIA
# ==============================================================================
# Abre o TXT na codificação 'latin-1' (Padrão legado do Datasus)
with open(arquivo, 'r', encoding='latin-1', errors='ignore') as f:
    for linha in f:
        
        # Filtro de Sanidade: Só lê a linha se ela for grande o suficiente e começar com número
        if len(linha) > POSICAO_SEXO and re.match(r'\d{15}', linha):
            total_lidos += 1
            
            sus = linha[:15].strip() # Os primeiros 15 caracteres são o Cartão SUS
            sexo = linha[POSICAO_SEXO].upper() # Pega a letra exata da posição 53
            
            # Passo 1: Validação Matemática (Módulo 11)
            # Se o Cartão for falso ou digitado errado, a gente nem audita, só ignora.
            if not valida_cns(sus):
                invalidos_matematicamente += 1
                continue 
                
            # Passo 2: O SUS é verdadeiro, mas a pessoa está sem sexo definido?
            if sexo not in ['M', 'F', 'I']:
                sus_para_corrigir.append(sus)

# list(set()) é um truque Pythonico brilhante para remover itens duplicados de uma lista
sus_para_corrigir = list(set(sus_para_corrigir))

# ==============================================================================
# 3. GERAÇÃO DO RELATÓRIO DE AÇÃO
# ==============================================================================
print("==================================================")
print(f"📊 Total de pacientes analisados: {total_lidos}")
print(f"🚫 SUS descartados por erro matemático: {invalidos_matematicamente}")
print(f"🚨 SUS válidos que precisam de correção de sexo: {len(sus_para_corrigir)}")
print("==================================================")

if sus_para_corrigir:
    # Se houver erros, ele cria um arquivo TXT novo com a lista para o Robô consertar depois
    with open("lista_correcao.txt", "w", encoding='utf-8') as out:
        for s in sus_para_corrigir:
            out.write(s + "\n")
    print(f"\n✅ Lista 'lista_correcao.txt' gerada com sucesso!")
    print(f"👉 Agora o Injetor TXT vai rodar apenas com números que o BPA aceita.")
else:
    print("\n🎉 Nenhum erro encontrado ou todos os erros eram de SUS matematicamente inválidos.")