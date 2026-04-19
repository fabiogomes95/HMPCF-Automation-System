# ==============================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO DE UTILIDADES (UTILS.PY)
# ==============================================================================
# OBJETIVO:
# Este arquivo atua como o "Motor de Limpeza" e validação do sistema. 
# Ele não cria telas ou exporta planilhas sozinho; em vez disso, ele é 
# "importado" pelos outros robôs e scripts para higienizar dados corrompidos
# e garantir a qualidade da informação antes que ela toque no Banco de Dados.
# ==============================================================================

import re           # Módulo 'Regular Expressions' (Regex) - Ferramenta de caça a padrões textuais.
import unicodedata  # Módulo para lidar com caracteres especiais e normalização de codificação de texto.

# ==============================================================================
# 1. FUNÇÃO DE LIMPEZA DE NÚMEROS (DATA EXTRATOR)
# ==============================================================================
def apenas_numeros(valor):
    """
    Função essencial para limpar documentos sujos e formatados de forma irregular 
    pela recepção (ex: '123.456.789-00' ou ' 12345678900_ ' -> '12345678900').
    """
    if not valor: return ""
    
    # O comando r'\D' é o código Regex para "Tudo o que NÃO for um dígito (número)".
    # O re.sub substitui todos os pontos, espaços e letras encontrados por "nada" (''), 
    # deixando sobrar estritamente os números.
    return re.sub(r'\D', '', str(valor))

# ==============================================================================
# 2. FUNÇÃO DE PADRONIZAÇÃO DE TEXTOS (DATA CLEANING)
# ==============================================================================
def remove_accents(input_str):
    """
    Remove acentos, cedilhas e caracteres estranhos, transformando tudo em MAIÚSCULO.
    Isso é vital em bancos de dados relacionais para que pesquisas futuras não tratem 
    "João" e "JOAO" como duas pessoas diferentes.
    """
    if not input_str: return ""
    
    # O formato 'NFKD' separa matematicamente as letras base dos seus acentos 
    # (ex: a letra 'á' é desmembrada em duas partes: 'a' + '´').
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    
    # List Comprehension: Cria uma nova string pegando apenas os caracteres normais 
    # e ignorando as marcas de acento (combining characters).
    limpo = "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()
    
    # O encode/decode em 'ascii' atua como uma barreira final de segurança. 
    # Ele arranca emojis ou caracteres invisíveis que o Windows possa ter copiado da internet.
    return limpo.encode('ascii', 'replace').decode('ascii').replace('?', ' ')

# ==============================================================================
# 3. VALIDAÇÃO MATEMÁTICA DO DATASUS (MÓDULO 11)
# ==============================================================================
def valida_cns(cns):
    """
    O coração da segurança do faturamento. Executa o algoritmo oficial do 
    Ministério da Saúde para confirmar se a sequência de 15 números forma 
    um Cartão SUS verdadeiro ou se foi inventada.
    """
    cns_l = apenas_numeros(cns)
    
    # Filtro de Sanidade: O SUS precisa ter exatos 15 números e começar 
    # obrigatoriamente com o prefixo 1, 2, 7, 8 ou 9.
    if not cns_l or len(cns_l) != 15 or cns_l not in '12789': return False
    
    # Lógica do Algoritmo Módulo 11 (usando For Loop inline e Sum):
    # Pega cada número do cartão SUS e multiplica por um peso decrescente 
    # (do 15 até o 1). Depois soma o resultado de todas essas 15 multiplicações.
    soma = sum(int(cns_l[i]) * (15 - i) for i in range(15))
    
    # Se o resto absoluto da divisão dessa grande soma por 11 for zero (0),
    # o cartão está matematicamente correto e autêntico!
    return soma % 11 == 0

# ==============================================================================
# 4. MINERAÇÃO E FATIAMENTO ESPACIAL (DATA MINING)
# ==============================================================================
def parse_endereco_fixed(endereco):
    """
    Algoritmo de Fatiamento Inteligente: Analisa uma linha corrida e sem padrão
    (ex: "Rua das Flores, 123B - Centro") e descobre de forma autônoma o que é a Rua,
    o que é o Número e o que é o Bairro. Fundamental para a Sincronização em Contingência.
    """
    if not endereco or len(str(endereco)) < 5: return "NAO INFORMADO", "S/N", ""
    
    # Passo 1: Limpeza prévia. Se a recepcionista colou o CEP (ex: 59575-000) no final, 
    # apagamos ele com Regex para o sistema não achar que o CEP é o número da casa.
    endereco = re.sub(r'\d{4,5}-\d{4}$', '', str(endereco)).strip()
    endereco = remove_accents(endereco).strip()
    
    # Passo 2: O Caçador (Regex finditer) procura blocos de dígitos (\d+) ou
    # detecta se as palavras 'S/N' ou 'SN' foram explicitamente digitadas.
    matches = list(re.finditer(r'\d+|\bS/N\b|\bSN\b', endereco))
    
    # Se não achou nenhum número na frase, presume que é uma rua sem número ("S/N").
    if not matches: return endereco[:30], "S/N", ""
    
    # Passo 3: Geralmente, a última sequência numérica isolada de uma frase é o número da residência.
    best_m = matches[-1]
    
    # Fatiamento Cirúrgico:
    # A RUA é todo o texto que vem ANTES do número. O .strip remove as vírgulas e traços encostados.
    rua = endereco[:best_m.start()].strip('., -')
    
    # O NÚMERO exato que o Regex encontrou.
    numero = best_m.group().strip()
    
    # O BAIRRO é todo o texto que vem DEPOIS do número.
    bairro = endereco[best_m.end():].strip('., -')
    
    # Retorna uma 'Tupla' fatiando a string nos limites de largura oficiais do banco de dados
    # (Ex: Máximo de 30 letras para o Bairro, e 5 letras para o número da casa).
    return rua[:30], numero[:5], bairro[:30]