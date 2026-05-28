"""
UTILS.PY — Motor de Validação e Limpeza de Dados
==================================================
Eu criei esse módulo para centralizar todas as funções
de validação e higienização de dados do sistema.

Aqui moram:
- Limpeza de números (CPF, SUS, telefone)
- Remoção de acentos (padronização de nomes)
- Validação de Cartão SUS (algoritmo oficial do Ministério da Saúde)
- Validação de CPF (algoritmo oficial da Receita Federal)
- Parse de endereço (separar rua, número e bairro de uma string bagunçada)

Isso evita que eu fique repetindo código em cada script do projeto.
"""

import re
# re = expressões regulares — uso pra varrer strings e extrair ou substituir padrões
import unicodedata
# unicodedata — uso pra normalizar caracteres unicode (remover acentos)


def apenas_numeros(valor: str | None) -> str:
    """
    Extrai APENAS os dígitos numéricos de qualquer bagunça.
    Exemplo: '123.456.789-00' vira '12345678900'
    Se vier None ou vazio, devolve string vazia pra não quebrar o código.
    """
    if not valor:
        return ""
    # re.sub(r'\D', '', ...) substitui TUDO que não é dígito por nada
    return re.sub(r'\D', '', str(valor))


def remove_accents(input_str: str | None) -> str:
    """
    Remove acentos, cecedilhas e caracteres especiais, devolvendo MAIÚSCULO.
    Exemplo: 'João Souza' vira 'JOAO SOUZA'
    Isso é crucial porque o sistema BPA do governo não aceita acentos.
    """
    if not input_str:
        return ""
    # NFKD "decompõe" caracteres acentuados: 'ã' vira 'a' + til (~)
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    # Filtro: mantenho só os caracteres que NÃO são combining marks (acentos)
    limpo = "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()
    # Forço ASCII e troco o que sobrou (tipo '?' de caracteres estranhos) por espaço
    return limpo.encode('ascii', 'replace').decode('ascii').replace('?', ' ')


def valida_cns(cns: str | None) -> bool:
    """
    Valida Cartão Nacional de Saúde usando o algoritmo oficial.
    
    O CNS tem 15 dígitos. O primeiro dígito diz o tipo:
    - 1 ou 2: CNS definitivo (válido por toda vida)
    - 7, 8 ou 9: CNS provisório (gerado na hora, segue regra diferente)
    
    Pra saber se é válido, eu faço uma soma ponderada (Módulo 11)
    e confiro se o dígito verificador bate.
    """
    cns_l = apenas_numeros(cns)
    # CNS TEM QUE TER 15 DÍGITOS — se não tiver, já era
    if len(cns_l) != 15 or cns_l[0] not in '12789':
        return False

    # --- CNS PROVISÓRIO (começa com 7, 8 ou 9) ---
    # Regra mais simples: soma ponderada direto nos 15 dígitos
    if cns_l[0] in '789':
        soma = sum(int(cns_l[i]) * (15 - i) for i in range(15))
        # O resto da divisão por 11 TEM que ser 0
        return soma % 11 == 0

    # --- CNS DEFINITIVO (começa com 1 ou 2) ---
    # Regra em duas etapas: primeiro calcula o DV nos 11 primeiros dígitos
    pis = cns_l[:11]  # Os 11 primeiros dígitos = "PIS" do CNS
    soma = sum(int(pis[i]) * (15 - i) for i in range(11))
    resto = soma % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    if dv == 10:
        # Caso especial: o DV deu 10, preciso somar 2 e recalcular
        soma += 2
        resto = soma % 11
        dv = 11 - resto
        resultado = pis + "001" + str(dv)
    else:
        # Caso normal: concateno "000" + DV nos 11 dígitos
        resultado = pis + "000" + str(dv)

    # Comparo o CNS calculado com o que foi passado
    return cns_l == resultado


def parse_endereco_fixed(endereco: str | None) -> tuple[str, str, str]:
    """
    Fatia um endereço bagunçado em TRÊS partes: Rua, Número e Bairro.
    
    O problema original: a recepção digitava o endereço tudo junto
    tipo "RUA DAS FLORES, 123. CENTRO" e eu precisava separar.
    
    Uso regex pra achar o ÚLTIMO número (ou "S/N") na string,
    pq o padrão dos endereços aqui é: RUA + NÚMERO + BAIRRO.
    
    Retorno uma tupla com (rua, numero, bairro) — cada um com no máximo 30 caracteres.
    """
    if not endereco or len(str(endereco)) < 5:
        # Se veio vazio ou muito pequeno, não tem o que separar
        return "NAO INFORMADO", "S/N", ""

    # Primeiro: removo telefone no final (ex: "84 99999-9999" no fim do endereço)
    endereco = re.sub(r'\d{4,5}-\d{4}$', '', str(endereco)).strip()
    # Depois: tiro acentos e padronizo
    endereco = remove_accents(endereco).strip()

    # Regex que acha TODOS os números ou "S/N" ou "SN" no texto
    matches = list(re.finditer(r'\d+|\bS/N\b|\bSN\b', endereco))
    if not matches:
        # Se não achou NADA, devolvo o endereço inteiro como rua
        return endereco[:30], "S/N", ""

    # Pego o ÚLTIMO match (o último número encontrado)
    # Por que o último? Porque o padrão "RUA 1, 2. BAIRRO" —
    # o último número tende a ser o número da casa.
    best_m = matches[-1]
    rua = endereco[:best_m.start()].strip('., -')
    numero = best_m.group().strip()
    bairro = endereco[best_m.end():].strip('., -')

    return rua[:30], numero[:5], bairro[:30]


def valida_cpf(cpf: str | None) -> bool:
    """
    Valida CPF usando o algoritmo oficial da Receita Federal (Módulo 11 duplo).
    
    O CPF tem 11 dígitos: 9 "base" + 2 dígitos verificadores (DV1 e DV2).
    
    Passo 1: multiplico cada dígito dos 9 primeiros por 10,9,8,7,6,5,4,3,2
    Passo 2: somo tudo, multiplico por 10, pego o resto de 11
    Passo 3: se deu 10, vira 0 — esse é o DV1, que confiro com o 10º dígito
    Passo 4: repito incluindo o DV1 pra achar o DV2
    
    Detalhe: sequências iguais (111.111.111-11) passam no algoritmo
    mas são inválidas — eu bloqueio elas manualmente.
    """
    cpf_l = apenas_numeros(cpf)

    # Se não tem 11 dígitos ou todos são iguais (ex: 000.000.000-00), é inválido
    if not cpf_l or len(cpf_l) != 11 or len(set(cpf_l)) == 1:
        return False

    # --- Cálculo do 1º dígito verificador ---
    # Multiplico cada dígito por (10 - posição), posição 0 a 8
    soma_1 = sum(int(cpf_l[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10

    # --- Cálculo do 2º dígito verificador ---
    # Agora uso 11 dígitos (incluindo o DV1 que acabei de calcular)
    soma_2 = sum(int(cpf_l[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10

    # Confiro se os dois dígitos calculados batem com os informados
    return str(digito_1) == cpf_l[9] and str(digito_2) == cpf_l[10]
