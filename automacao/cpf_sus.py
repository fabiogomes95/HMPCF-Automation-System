"""
CPF_SUS.PY — Extrator/Validador Inteligente de CPF e SUS
==========================================================
Esse módulo é o "limpador" de dados sujos.

O problema original: a triagem recebe listas bagunçadas com
nomes, CPFs e SUSs misturados — tipo:
    "MARIA 123.456.789-00 898765432109876 JOAO"

O que ele faz:
1. Lê o arquivo sujo (cpf_sus.txt)
2. Varre cada linha em busca de números
3. Testa se é CPF (11 dígitos válido) ou SUS (15 dígitos válido)
4. Prioriza SUS (mais confiável pro BPA)
5. Devolve lista limpa de documentos

Tudo na MEMÓRIA — sem criar arquivos temporários.
"""

import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, valida_cns, valida_cpf


def processar_lista(caminho_arquivo_sujo):
    """
    Lê o arquivo com dados bagunçados e extrai CPFs/SUSs válidos.
    
    Parâmetros:
        caminho_arquivo_sujo: path pro cpf_sus.txt
    
    Como funciona:
    1. Pega cada linha do arquivo
    2. Separa as "palavras" (split por espaço)
    3. Cada palavra: extrai números e testa
    4. Se for SUS (15 dígitos + válido) → guarda
    5. Se for CPF (11 dígitos + válido) → guarda (se não achou SUS)
    6. Prioridade: SUS > CPF
    
    Retorna lista de strings (documentos limpos).
    """
    try:
        with open(caminho_arquivo_sujo, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        return []  # Vazio pro painel mostrar o erro

    resultado_limpo = []

    for linha in linhas:
        if not linha.strip():
            continue

        # Separo por espaços
        partes = linha.split()

        sus_encontrado = ""
        cpf_encontrado = ""

        for p in partes:
            # Extraio só os números da "palavra"
            num = apenas_numeros(p)

            # Testa se é SUS (15 dígitos + algoritmo CNS)
            if len(num) == 15 and valida_cns(num):
                sus_encontrado = num

            # Testa se é CPF (11 dígitos + algoritmo Receita Federal)
            elif len(num) == 11 and valida_cpf(num):
                cpf_encontrado = num

        # Regra de prioridade: SUS > CPF
        if sus_encontrado:
            resultado_limpo.append(sus_encontrado)
        elif cpf_encontrado:
            resultado_limpo.append(cpf_encontrado)

    return resultado_limpo
