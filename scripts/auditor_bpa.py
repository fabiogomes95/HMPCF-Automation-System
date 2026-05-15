"""
AUDITOR_BPA.PY — Auditor de Sexo em TXT BPA
==============================================
Esse script lê o arquivo TXT gerado pelo sistema do governo (Datasus)
e verifica se o campo SEXO (posição 53) está preenchido corretamente.

O layout posicional do BPA determina que:
- Caracteres 0-14: CNS (Cartão SUS)
- Caractere 53: Sexo (M, F ou I)

O que o auditor faz:
1. Lê o ExpPaciente.txt
2. Pra cada linha, valida o SUS (algoritmo CNS)
3. Se o SUS é válido mas o sexo está vazio/errado → lista pra correção
4. Gera lista_correcao.txt pro Robô RPA corrigir depois

Uso: python scripts/auditor_bpa.py
(Precisa do ExpPaciente.txt na mesma pasta)
"""

import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import valida_cns

print("==================================================")
print("AUDITORIA BPA: POSICAO 53 + VALIDACAO CNS")
print("==================================================\n")

arquivo = "ExpPaciente.txt"
if not os.path.exists(arquivo):
    print(f"Arquivo '{arquivo}' nao encontrado.")
    exit()

# No layout do governo, o campo Sexo fica no caractere 53
POSICAO_SEXO = 53

sus_para_corrigir = []
total_lidos = 0
invalidos_matematicamente = 0

# --- VARREDURA DO ARQUIVO ---
with open(arquivo, 'r', encoding='latin-1', errors='ignore') as f:
    for linha in f:
        # Só processa linhas grandes o suficiente e que começam com 15 dígitos
        if len(linha) > POSICAO_SEXO and re.match(r'\d{15}', linha):
            total_lidos += 1

            sus = linha[:15].strip()
            sexo = linha[POSICAO_SEXO].upper()

            # PASSO 1: Validação matemática do SUS
            if not valida_cns(sus):
                invalidos_matematicamente += 1
                continue

            # PASSO 2: Sexo inválido/vazio?
            if sexo not in ['M', 'F', 'I']:
                sus_para_corrigir.append(sus)

# Remove duplicatas (um mesmo SUS pode aparecer várias vezes)
sus_para_corrigir = list(set(sus_para_corrigir))

print("==================================================")
print(f"Total de pacientes analisados: {total_lidos}")
print(
    f"SUS descartados (erro matematico): "
    f"{invalidos_matematicamente}"
)
print(
    f"SUS validos que precisam de correcao de sexo: "
    f"{len(sus_para_corrigir)}"
)
print("==================================================")

if sus_para_corrigir:
    # Gera a lista pro Robô RPA corrigir depois
    with open("lista_correcao.txt", "w", encoding='utf-8') as out:
        for s in sus_para_corrigir:
            out.write(s + "\n")
    print("\nLista 'lista_correcao.txt' gerada!")
    print("Agora execute o Robo RPA para corrigir.")
else:
    print("\nNenhum erro encontrado.")
