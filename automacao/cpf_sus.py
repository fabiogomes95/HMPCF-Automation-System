import re

# ==============================================================================
# FUNÇÕES DE VALIDAÇÃO (Regras oficiais do DATASUS e Receita Federal)
# ==============================================================================

def apenas_numeros(valor):
    """Remove pontos, traços e espaços, mantendo apenas os dígitos."""
    return re.sub(r'\D', '', str(valor))

def valida_cns(cns):
    """Valida o Cartão Nacional de Saúde (SUS) usando o Módulo 11."""
    if not cns or len(cns) != 15 or cns[0] not in '12789': 
        return False
    soma = sum(int(cns[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

def valida_cpf(cpf):
    """Valida o CPF através dos dígitos verificadores."""
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1: 
        return False
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]

# ==============================================================================
# PROCESSAMENTO DO ARQUIVO (LÓGICA DE PRIORIDADE: SUS > CPF)
# ==============================================================================

def processar_lista():
    """Lê o rascunho cpf_sus.txt e salva APENAS UM documento por linha no pacientes.txt."""
    try:
        with open("cpf_sus.txt", "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        print("Erro: O arquivo cpf_sus.txt não foi encontrado.")
        return

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

        # --- A REGRA DE OURO ---
        if sus_encontrado:
            resultado_limpo.append(sus_encontrado)
        elif cpf_encontrado:
            resultado_limpo.append(cpf_encontrado)

    # Salva no TXT
    try:
        with open("pacientes.txt", "w", encoding="utf-8") as f_out:
            for doc in resultado_limpo:
                f_out.write(f"{doc}\n")
        print(f"✅ Concluído! {len(resultado_limpo)} documentos limpos.")
    except Exception as e:
        print(f"Erro ao salvar: {e}")

if __name__ == "__main__":
    processar_lista()