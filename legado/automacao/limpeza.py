"""
Processa listas de CPF/SUS extraindo documentos válidos.
Remove duplicatas consecutivas (digitação dupla acidental).
"""

import re


def apenas_numeros(valor):
    return re.sub(r'\D', '', str(valor))

def valida_cns(cns):
    if not cns or len(cns) != 15 or cns[0] not in '12789':
        return False
    if cns[0] in '789':
        return sum(int(cns[i]) * (15 - i) for i in range(15)) % 11 == 0
    pis = cns[:11]
    soma = sum(int(pis[i]) * (15 - i) for i in range(11))
    resto = soma % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    if dv == 10:
        soma += 2
        resto = soma % 11
        dv = 11 - resto
        resultado = pis + "001" + str(dv)
    else:
        resultado = pis + "000" + str(dv)
    return cns == resultado

def valida_cpf(cpf):
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]

def processar_lista(caminho_arquivo_sujo):
    try:
        with open(caminho_arquivo_sujo, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        return []

    resultado_limpo = []
    ultimo = None

    for linha in linhas:
        if not linha.strip():
            continue

        sus_encontrado = ""
        cpf_encontrado = ""

        for p in linha.split():
            num = apenas_numeros(p)
            if len(num) == 15 and valida_cns(num):
                sus_encontrado = num
            elif len(num) == 11 and valida_cpf(num):
                cpf_encontrado = num

        escolhido = sus_encontrado or cpf_encontrado

        if escolhido and escolhido != ultimo:
            ultimo = escolhido
            resultado_limpo.append(escolhido)

    return resultado_limpo
