# ==============================================================================
# 🩺 MÓDULO DIGITADOR MANUAL: BUSCA, MÁSCARAS E CORTE DE 99 LOTES
# ==============================================================================

import os
import re

def aplicar_mascara(lista_pacientes):
    """Cria uma cópia da lista e coloca pontos e espaços para a tela do HTML ficar linda."""
    lista_formatada = []
    for p in lista_pacientes:
        sus = p['sus']
        cpf = p['cpf']
        
        sus_fmt = f"{sus[0:3]} {sus[3:7]} {sus[7:11]} {sus[11:15]}" if len(sus) == 15 else sus
        cpf_fmt = f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}" if len(cpf) == 11 else cpf
        
        lista_formatada.append({
            'nome': p['nome'],
            'dtnasc': p['dtnasc'],
            'sus': sus_fmt,
            'cpf': cpf_fmt
        })
    return lista_formatada

def buscar_pacientes_memoria(termo, base_pacientes_ram):
    """Faz a busca ignorando as máscaras que você digita na tela do navegador."""
    if not termo: 
        return aplicar_mascara(base_pacientes_ram[:50])
        
    termo_original = termo.upper().strip()
    
    # Extrai só os números (ignora pontos da pesquisa do usuário)
    termo_so_numeros = "".join([c for c in termo if c.isdigit()])
    
    resultados = []
    
    for p in base_pacientes_ram:
        if termo_original in p['nome']:
            resultados.append(p)
        elif termo_so_numeros and (termo_so_numeros in p['sus'] or termo_so_numeros in p['cpf']):
            resultados.append(p)
            
        if len(resultados) == 50: 
            break
            
    return aplicar_mascara(resultados)

def criar_cabecalho_producao(caminho_completo, medico, data):
    """Gera o cabeçalho inicial quando você vai começar a digitar a produção."""
    try:
        with open(caminho_completo, 'a', encoding='utf-8') as f:
            f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")
        return True
    except Exception as e:
        print(f"Erro ao criar cabeçalho manual: {e}")
        return False

def adicionar_ficha_producao(caminho_completo, documento):
    """
    1. Arranca todas as máscaras que vieram do navegador (salva apenas números).
    2. Lê o arquivo de trás pra frente e conta as fichas do médico.
    3. Se bater 99, cria um lote novo para continuar salvando.
    """
    # 1. Limpa tudo e deixa o número puro pro robô
    doc_limpo = re.sub(r'\D', '', str(documento)).strip()
    
    try:
        pacientes_no_lote = 0
        ultimo_cabecalho = ""
        
        # 2. Faz a varredura lendo de baixo pra cima
        if os.path.exists(caminho_completo):
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
            
            for linha in reversed(linhas):
                linha_limpa = linha.strip()
                if not linha_limpa: continue
                
                if linha_limpa.startswith("PROFISSIONAL:"):
                    ultimo_cabecalho = linha_limpa
                    break
                else:
                    pacientes_no_lote += 1
                    
        with open(caminho_completo, 'a', encoding='utf-8') as f:
            # 3. Regra dos 99: Se estourou a cota, duplica o cabeçalho pra criar lote novo
            if pacientes_no_lote >= 99 and ultimo_cabecalho:
                f.write(f"\n{ultimo_cabecalho}\n")
                
            f.write(f"{doc_limpo}\n")
            
        return True
    except Exception as e:
        print(f"Erro ao salvar ficha manual: {e}")
        return False