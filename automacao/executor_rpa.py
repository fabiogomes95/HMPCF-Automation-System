import pyautogui    
import time         
import os           
import sys          
import re           
import keyboard      
import firebirdsql  

# Trava de segurança
pyautogui.FAILSAFE = True 
caminho_gdb = r'C:/BPA/BPAMAG.GDB'

def preparar_lotes(arq_leitura):
    """Função que o Fábio usa para cruzar o TXT com o GDB"""
    base_oficial = {}
    try:
        con = firebirdsql.connect(host='localhost', database=caminho_gdb, user='SYSDBA', password='masterkey', charset='WIN1252')
        cur = con.cursor()
        cur.execute("SELECT CNS, NUM_CPF FROM CADCNS")
        for r in cur.fetchall():
            sus = str(r[0] or "").strip()
            cpf = str(r[1] or "").strip()
            if len(sus) == 15: base_oficial[sus] = True
            if len(cpf) == 11: base_oficial[cpf] = True
        con.close()
    except Exception as e: return [], f"Erro banco: {e}"

    lotes = []
    lote_atual = None
    with open(arq_leitura, 'r', encoding='utf-8', errors='ignore') as f:
        linhas = f.readlines()
    
    for linha in linhas:
        ln = linha.upper().strip()
        if not ln: continue
        if "PROFISSIONAL:" in ln:
            parts = ln.split("|")
            med = parts[0].replace("PROFISSIONAL:", "").strip()
            dt = parts[1].replace("DATA:", "").strip() if len(parts) > 1 else "00000000"
            lote_atual = {'medico': med, 'data': dt, 'pacientes': []}
            lotes.append(lote_atual)
        elif lote_atual:
            num = "".join(re.findall(r'\d+', ln))
            if len(num) in (11, 15): lote_atual['pacientes'].append(num)

    lotes_v = []
    for l in lotes:
        v = [p for p in l['pacientes'] if p in base_oficial]
        if v:
            l['validados'] = v
            lotes_v.append(l)
    return lotes_v, ""

def executar_pyautogui(medico, data_atend, procedimento, pacientes, callback=None):
    """Execução física das teclas"""
    total = len(pacientes)
    for i, p in enumerate(pacientes, 1):
        # Verifica se o Fábio apertou ESC para parar
        if keyboard.is_pressed('esc'):
            if callback: callback("🛑 INTERROMPIDO PELO USUÁRIO")
            pyautogui.alert("Robô Pausado. Clique OK para continuar de onde parou.")

        if callback: callback(f"🚀 Lote de {medico} | Paciente {i} de {total}")

        try:
            # Sequência BPA
            pyautogui.write(p); pyautogui.press('f7'); time.sleep(1.2)          
            pyautogui.write(data_atend); pyautogui.press('tab')
            pyautogui.write(procedimento); pyautogui.press('1'); time.sleep(0.5)
            pyautogui.press(['tab', 'tab', 'tab']); pyautogui.write('2'); time.sleep(0.3)
            pyautogui.press(['tab', 'tab']); pyautogui.press('enter')
            time.sleep(1.0)
        except:
            break