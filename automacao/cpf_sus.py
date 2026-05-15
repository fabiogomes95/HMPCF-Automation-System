import re
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, valida_cns, valida_cpf

# ==============================================================================
# 🧹 PROCESSAMENTO NA MEMÓRIA (Sem arquivos de lixo)
# ==============================================================================

def processar_lista(caminho_arquivo_sujo):
    """
    Lê o rascunho sujo salvo pelo painel, limpa tudo e 
    devolve a lista de CPFs/SUS purinha em formato de código.
    """
    try:
        with open(caminho_arquivo_sujo, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        return [] # Retorna vazio pro painel dar o aviso

    resultado_limpo = []

    for linha in linhas:
        if not linha.strip(): continue 
        partes = linha.split() 
        
        sus_encontrado = ""
        cpf_encontrado = ""

        for p in partes:
            num = apenas_numeros(p)
            if len(num) == 15 and valida_cns(num):
                sus_encontrado = num
            elif len(num) == 11 and valida_cpf(num):
                cpf_encontrado = num

        # Prioriza SUS. Se não tiver, vai o CPF.
        if sus_encontrado:
            resultado_limpo.append(sus_encontrado)
        elif cpf_encontrado:
            resultado_limpo.append(cpf_encontrado)

    return resultado_limpo