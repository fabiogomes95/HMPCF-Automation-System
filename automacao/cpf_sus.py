import re

# ==============================================================================
# FUNÇÕES DE VALIDAÇÃO (Embutidas para não depender de outros arquivos)
# ==============================================================================
def apenas_numeros(valor):
    return re.sub(r'\D', '', str(valor))

def valida_cns(cns):
    if not cns or len(cns) != 15 or cns[0] not in '12789': return False
    soma = sum(int(cns[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

def valida_cpf(cpf):
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1: return False
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]

# ==============================================================================
# PROCESSAMENTO DO ARQUIVO
# ==============================================================================
def processar_lista():
    try:
        # Lê o seu arquivo original
        with open('cpf_sus.txt', 'r', encoding='utf-8') as f:
            linhas = f.readlines()
    except FileNotFoundError:
        print("❌ Arquivo 'cpf_sus.txt' não encontrado na pasta.")
        return

    limpos = []

    for linha in linhas:
        partes = linha.split()
        sus_valido = ""
        cpf_valido = ""

        # Analisa os pedaços separados por espaço/tab
        for p in partes:
            num = apenas_numeros(p)
            
            # Testa se é um SUS perfeito
            if len(num) == 15 and valida_cns(num):
                sus_valido = num
            # Testa se é um CPF perfeito
            elif len(num) == 11 and valida_cpf(num):
                cpf_valido = num

        # A PRIORIDADE É O SUS
        if sus_valido:
            limpos.append(sus_valido)
        # SE NÃO TIVER SUS VÁLIDO, USA O CPF
        elif cpf_valido:
            limpos.append(cpf_valido)

    # Cria o arquivo final limpo para o robô
    with open('pacientes_limpos.txt', 'w', encoding='utf-8') as f_out:
        for doc in limpos:
            f_out.write(f"{doc}\n")

    print(f"✅ Limpeza concluída!")
    print(f"📄 Dos {len(linhas)} registros originais, {len(limpos)} documentos válidos foram salvos.")
    print(f"👉 Arquivo gerado: 'pacientes_limpos.txt'. Use este no seu robô!")

if __name__ == "__main__":
    processar_lista()