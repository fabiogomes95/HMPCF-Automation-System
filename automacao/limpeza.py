import re

# ==============================================================================
# 🛡️ FUNÇÕES DE VALIDAÇÃO OFICIAIS (DATASUS / RECEITA FEDERAL)
# ==============================================================================

def apenas_numeros(valor):
    return re.sub(r'\D', '', str(valor))

def valida_cns(cns):
    if not cns or len(cns) != 15 or cns[0] not in '12789':
        return False
    soma = sum(int(cns[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

def valida_cpf(cpf):
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]

# ==============================================================================
# 🧹 PROCESSAMENTO NA MEMÓRIA (Sem arquivos de lixo)
# ==============================================================================

def processar_lista(caminho_arquivo_sujo):
    try:
        with open(caminho_arquivo_sujo, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        return []

    resultado_limpo = []
    vistos = set()  # ✅ Controle de duplicatas

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

        # Prioriza SUS. Se não tiver, vai o CPF.
        escolhido = sus_encontrado or cpf_encontrado

        # ✅ Só adiciona se for válido e ainda não visto
        if escolhido and escolhido not in vistos:
            vistos.add(escolhido)
            resultado_limpo.append(escolhido)

    return resultado_limpo