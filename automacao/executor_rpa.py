import pyautogui    
import time         
import os           
import sys          
import keyboard      

# Trava de Segurança (Jogue o mouse pro canto da tela se quiser que o robô pare na marra)
pyautogui.FAILSAFE = True 

def preparar_lotes(arq_leitura, base_pacientes_ram=None):
    """Lê o arquivo de produção e organiza as 'pilhas' de fichas de forma instantânea."""
    if not os.path.exists(arq_leitura):
        return [], "Ficheiro não encontrado."

    # Filtro super rápido na RAM usando a memória enviada pelo painel
    documentos_validos = set()
    if base_pacientes_ram:
        for p in base_pacientes_ram:
            if p.get('sus'): documentos_validos.add(p['sus'])
            if p.get('cpf'): documentos_validos.add(p['cpf'])

    with open(arq_leitura, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    lotes = []
    lote_atual = None

    for linha in linhas:
        linha = linha.strip()
        if not linha: continue

        if "PROFISSIONAL:" in linha:
            if lote_atual: lotes.append(lote_atual)
            
            partes = linha.split('|')
            medico = partes[0].replace("PROFISSIONAL:", "").strip()
            data = partes[1].replace("DATA:", "").strip()
            
            lote_atual = {
                'medico': medico,
                'data': data,
                'pacientes': [],
                'validados': []
            }
        elif lote_atual:
            # Validação Mágica: Testa contra a RAM em 0.0001 segundo sem travar
            if not base_pacientes_ram or linha in documentos_validos:
                lote_atual['validados'].append(linha)
            lote_atual['pacientes'].append(linha)

    if lote_atual: lotes.append(lote_atual)
    return lotes, ""

def executar_pyautogui(medico, data_atend, procedimento, pacientes, callback=None):
    """A rotina de digitação física do Robô RPA."""
    
    # Limpeza da data (Remove barras, mantendo apenas números)
    data_limpa = "".join([c for c in data_atend if c.isdigit()])
    
    total = len(pacientes)
    for i, p in enumerate(pacientes, 1):
        if keyboard.is_pressed('esc'):
            if callback: callback("🛑 INTERROMPIDO PELO USUÁRIO (ESC)")
            break

        if callback: callback(f"🚀 {medico} | {i}/{total} | Doc: {p}")

        try:
            # ==============================================================================
            # LÓGICA DE TECLAS RESTAURADA (EXATAMENTE COMO VOCÊ CONFIGUROU)
            # ==============================================================================
            pyautogui.write(p)       
            pyautogui.press('f7')    
            time.sleep(1.0)          
            
            # Envia a data limpa (ex: 13042026) e dá o Tab
            pyautogui.write(data_limpa)
            pyautogui.press('tab')
            
            pyautogui.write(procedimento)
            pyautogui.press('1')     
            time.sleep(0.5)
            
            pyautogui.press(['tab', 'tab', 'tab']) 
            pyautogui.write('2')     
            time.sleep(0.3)
            
            pyautogui.press(['tab', 'tab'])
            pyautogui.press('enter') 
            
            time.sleep(1.2)
            # ==============================================================================
            
        except Exception as e:
            print(f"Erro na digitação: {e}")
            continue