# ==============================================================================
# 🩺 MÓDULO DIGITADOR MANUAL: BUSCA NA RAM E CORTE DE 99 LOTES
# ==============================================================================

import os
import re

def buscar_pacientes_memoria(termo, base_pacientes_ram):
    """
    Recebe o termo digitado na tela e filtra pela memória RAM sem aplicar máscaras.
    Isso garante a velocidade máxima na pesquisa!
    """
    if not termo: 
        return base_pacientes_ram[:50]
        
    termo = termo.upper().strip()
    resultados = []
    
    # Varre a memória da RAM na velocidade da luz
    for p in base_pacientes_ram:
        if termo in p['nome'] or termo in p['sus'] or termo in p['cpf']:
            resultados.append(p)
            
            # Trava cirúrgica para não sobrecarregar o HTML
            if len(resultados) == 50: 
                break
                
    return resultados

def criar_cabecalho_producao(caminho_completo, medico, data):
    """Gera o cabeçalho oficial que o Robô RPA consegue ler."""
    try:
        with open(caminho_completo, 'a', encoding='utf-8') as f:
            f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")
        return True
    except Exception as e:
        print(f"Erro ao criar cabeçalho manual: {e}")
        return False

def adicionar_ficha_producao(caminho_completo, documento):
    """
    Limpa o documento (garantia extra) e faz a quebra automática a cada 99 pacientes.
    """
    doc_limpo = re.sub(r'\D', '', str(documento)).strip()
    
    try:
        pacientes_no_lote = 0
        ultimo_cabecalho = ""
        
        # Faz a varredura lendo de baixo pra cima no arquivo .txt
        if os.path.exists(caminho_completo):
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
            
            for linha in reversed(linhas):
                linha_limpa = linha.strip()
                if not linha_limpa: continue
                
                # Procura quem foi o último médico registrado
                if linha_limpa.startswith("PROFISSIONAL:"):
                    ultimo_cabecalho = linha_limpa
                    break
                else:
                    pacientes_no_lote += 1
                    
        with open(caminho_completo, 'a', encoding='utf-8') as f:
            # ✂️ REGRA DOS 99: Se estourou a cota de 99 fichas, duplica o cabeçalho pra criar um lote novo!
            if pacientes_no_lote >= 99 and ultimo_cabecalho:
                f.write(f"\n{ultimo_cabecalho}\n")
                
            f.write(f"{doc_limpo}\n")
            
        return True
    except Exception as e:
        print(f"Erro ao salvar ficha manual: {e}")
        return False