import pyautogui    
import time         
import os           
import sys          
import re           
import keyboard      
import firebirdsql  

# Trava de segurança do PyAutoGUI: se o mouse for para o canto da tela, o robô para
pyautogui.FAILSAFE = True 
caminho_gdb = r'C:/BPA/BPAMAG.GDB'

def preparar_lotes(arq_leitura):
    """
    Lê o arquivo TXT de produção, organiza os pacientes em lotes (por Profissional e Data)
    e valida cada CPF/SUS contra a base de dados GDB para garantir que existem no BPA.
    """
    base_oficial = {}
    online = False
    
    # 1. Tenta conectar ao banco do BPA para carregar os documentos válidos
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
    
    # Verifica se o arquivo TXT existe
    if not os.path.exists(arq_leitura):
        return [], "Arquivo não encontrado."

    with open(arq_leitura, 'r', encoding='utf-8', errors='ignore') as f:
        linhas = f.readlines()
    
    # 2. Varre o arquivo linha por linha para criar os lotes
    for linha in linhas:
        ln = linha.upper().strip()
        if not ln: continue

        # Identifica a linha de cabeçalho do lote no formato exato: PROFISSIONAL: NOME | DATA: XX/XX/XXXX
        if "PROFISSIONAL:" in ln:
            parts = ln.split("|") # Quebra a linha usando o caractere |
            med = parts[0].replace("PROFISSIONAL:", "").strip()
            dt = parts[1].replace("DATA:", "").strip() if len(parts) > 1 else "00/00/0000"
            
            # Cria um novo lote para este profissional
            lote_atual = {'medico': med, 'data': dt, 'pacientes': [], 'validados': []}
            lotes.append(lote_atual)
            
        elif lote_atual:
            # Pega os números da linha (se for um documento SUS ou CPF)
            num = "".join(re.findall(r'\d+', ln))
            if len(num) in (11, 15):
                lote_atual['pacientes'].append(num)

    # 3. Filtragem: cruza os lotes com a base oficial (se estiver conectado)
    lotes_finais = []
    for l in lotes:
        if online:
            # Só mantém o paciente se ele existir no banco de dados do BPA
            l['validados'] = [p for p in l['pacientes'] if p in base_oficial]
        else:
            l['validados'] = l['pacientes']
            
        # Adiciona o lote final apenas se houver pacientes válidos nele
        if l['validados']:
            lotes_finais.append(l)

    if not lotes_finais:
        return [], "❌ Lote vazio ou sem o cabeçalho correto de PROFISSIONAL e DATA."
        
    return lotes_finais, ""

def executar_pyautogui(medico, data_atend, procedimento, pacientes, callback=None):
    """
    Controla o teclado para digitar os dados físicos no sistema BPA.
    Pode ser interrompido apertando a tecla 'ESC'.
    """
    total = len(pacientes)
    for i, p in enumerate(pacientes, 1):
        # Checa interrupção
        if keyboard.is_pressed('esc'):
            if callback: callback("🛑 INTERROMPIDO PELO USUÁRIO")
            return

        if callback: callback(f"🚀 {medico} | Paciente {i} de {total}")

        try:
            # A rotina de teclas (preenche documento, f7, data, enter, procedimento...)
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