# ==============================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO DE UTILIDADES (UTILS.PY)
# ==============================================================================
# OBJETIVO:
# Este arquivo atua como o "Motor de Limpeza" e validação do sistema. 
# Ele higieniza dados corrompidos e garante a qualidade da informação.
# ==============================================================================

import re           
import unicodedata  

# ==============================================================================
# 1. FUNÇÃO DE LIMPEZA DE NÚMEROS (DATA EXTRATOR)
# ==============================================================================
def apenas_numeros(valor):
    """Extrai apenas os dígitos de uma string corrompida."""
    if not valor: return ""
    return re.sub(r'\D', '', str(valor))

# ==============================================================================
# 2. FUNÇÃO DE PADRONIZAÇÃO DE TEXTOS (DATA CLEANING)
# ==============================================================================
def remove_accents(input_str):
    """Remove acentos e caracteres especiais, transformando em MAIÚSCULO."""
    if not input_str: return ""
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    limpo = "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()
    return limpo.encode('ascii', 'replace').decode('ascii').replace('?', ' ')

# ==============================================================================
# 3. VALIDAÇÃO MATEMÁTICA DO DATASUS (MÓDULO 11)
# ==============================================================================
def valida_cns(cns):
    """Executa o algoritmo oficial do Ministério da Saúde para validar o Cartão SUS."""
    cns_l = apenas_numeros(cns)
    
    # O SUS precisa ter 15 números e começar com 1, 2, 7, 8 ou 9.
    if not cns_l or len(cns_l) != 15 or cns_l[0] not in '12789': return False
    
    soma = sum(int(cns_l[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

# ==============================================================================
# 4. MINERAÇÃO E FATIAMENTO ESPACIAL (DATA MINING)
# ==============================================================================
def parse_endereco_fixed(endereco):
    """Fatia um endereço corrido em Rua, Número e Bairro."""
    if not endereco or len(str(endereco)) < 5: return "NAO INFORMADO", "S/N", ""
    
    endereco = re.sub(r'\d{4,5}-\d{4}$', '', str(endereco)).strip()
    endereco = remove_accents(endereco).strip()
    
    matches = list(re.finditer(r'\d+|\bS/N\b|\bSN\b', endereco))
    if not matches: return endereco[:30], "S/N", ""
    
    best_m = matches[-1]
    rua = endereco[:best_m.start()].strip('., -')
    numero = best_m.group().strip()
    bairro = endereco[best_m.end():].strip('., -')
    
    return rua[:30], numero[:5], bairro[:30]

# ==============================================================================
# 5. VALIDAÇÃO MATEMÁTICA DE CPF (MÓDULO 11 DUPLO)
# ==============================================================================
def valida_cpf(cpf):
    """Executa o cálculo oficial da Receita Federal para validar o CPF."""
    cpf_l = apenas_numeros(cpf)
    
    if not cpf_l or len(cpf_l) != 11 or len(set(cpf_l)) == 1: 
        return False
        
    soma_1 = sum(int(cpf_l[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    
    soma_2 = sum(int(cpf_l[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    
    return str(digito_1) == cpf_l[9] and str(digito_2) == cpf_l[10]