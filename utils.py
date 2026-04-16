import re
import unicodedata

def apenas_numeros(valor):
    """Remove tudo o que não for número (pontos, traços, espaços)."""
    if not valor: return ""
    return re.sub(r'\D', '', str(valor))

def remove_accents(input_str):
    """Padroniza strings: remove acentos e coloca em maiúsculo."""
    if not input_str: return ""
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    limpo = "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()
    return limpo.encode('ascii', 'replace').decode('ascii').replace('?', ' ')

def valida_cns(cns):
    """Validação matemática oficial do Módulo 11 para o CNS."""
    cns_l = apenas_numeros(cns)
    if not cns_l or len(cns_l) != 15 or cns_l[0] not in '12789': return False
    soma = sum(int(cns_l[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

def parse_endereco_fixed(endereco):
    """Fatia o endereço em Rua, Número e Bairro."""
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