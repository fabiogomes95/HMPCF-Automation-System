import pyautogui    
import time         
import os           
import sys          
import re           
import keyboard      
import firebirdsql  

# Trava de segurança do PyAutoGUI
pyautogui.FAILSAFE = True 
caminho_gdb = r'C:/BPA/BPAMAG.GDB'

def preparar_lotes(arq_leitura):
    """Lê o TXT e organiza os pacientes por Profissional e Data"""
    base_oficial = {}
    online = False
    
    # Tenta conectar ao banco para validar os números
    try:
        con = firebirdsql.connect(host='localhost', database=caminho_gdb, user='SYSDBA', password='masterkey', charset='WIN1252')
        cur = con.cursor()
        cur.execute("SELECT CNS, NUM_CPF FROM CADCNS")
        for r in cur.fetchall():
            sus, cpf = str(r[0] or "").strip(), str(r[1] or "").strip()
            if len(sus) == 15: base_oficial[sus] = True
            if len(cpf) == 11: base_oficial[cpf] = True
        con.close()
        online = True
    except:
        print("⚠️ Modo Offline: Ignorando validação de banco (GDB não encontrado).")

    lotes = []
    lote_atual = None
    
    if not os.path.exists(arq_leitura):
        return [], "Arquivo não encontrado."

    with open(arq_leitura, 'r', encoding='utf-8', errors='ignore') as f:
        linhas = f.readlines()
    
    for linha in linhas:
        ln = linha.upper().strip()
        if not ln: continue

        # Identifica a linha de cabeçalho PROFISSIONAL: ... | DATA: ...
        if "PROFISSIONAL:" in ln:
            parts = ln.split("|")
            med = parts[0].replace("PROFISSIONAL:", "").strip()
            dt = parts[1].replace("DATA:", "").strip() if len(parts) > 1 else "00/00/0000"
            
            lote_atual = {'medico': med, 'data': dt, 'pacientes': [], 'validados': []}
            lotes.append(lote_atual)
            
        elif lote_atual:
            # Extrai apenas os dígitos da linha
            num = "".join(re.findall(r'\d+', ln))
            if len(num) in (11, 15):
                lote_atual['pacientes'].append(num)

    # Filtragem: Se estiver online, remove o que não existe no banco.
    # Se estiver offline (casa), aceita tudo para teste.
    lotes_finais = []
    for l in lotes:
        if online:
            l['validados'] = [p for p in l['pacientes'] if p in base_oficial]
        else:
            l['validados'] = l['pacientes']
            
        if l['validados']:
            lotes_finais.append(l)

    if not lotes_finais:
        return [], "❌ Lote vazio ou sem o cabeçalho correto de PROFISSIONAL e DATA."
        
    return lotes_finais, ""

def executar_pyautogui(medico, data_atend, procedimento, pacientes, callback=None):
    """Executa a digitação física no BPA"""
    total = len(pacientes)
    for i, p in enumerate(pacientes, 1):
        if keyboard.is_pressed('esc'):
            if callback: callback("🛑 INTERROMPIDO PELO USUÁRIO")
            return

        if callback: callback(f"🚀 {medico} | Paciente {i} de {total}")

        try:
            pyautogui.write(p)
            pyautogui.press('f7')
            time.sleep(1.2)
            pyautogui.write(data_atend)
            pyautogui.press('enter')
            time.sleep(0.5)
            pyautogui.write(procedimento)
            pyautogui.press('enter', presses=2, interval=0.3)
            time.sleep(0.8)
        except Exception as e:
            if callback: callback(f"❌ Erro no paciente {p}: {e}")
            break