import pyautogui
import time
import os
import keyboard
import fdb

# ==============================================================================
# 🔥 CONEXÃO FIREBIRD
# ==============================================================================

FIREBIRD_CONFIG = {
    'host':     'localhost',
    'database': r'C:\BPA\BPAMAG.GDB',
    'user':     'SYSDBA',
    'password': 'masterkey',
    'charset':  'WIN1252'
}

def conectar_firebird():
    return fdb.connect(**FIREBIRD_CONFIG)

# ==============================================================================
# 🔍 VALIDAÇÃO NO BANCO (chamada dentro de preparar_lotes)
# ==============================================================================

def buscar_paciente_no_banco(documento: str) -> dict | None:
    if len(documento) == 15:
        campo = "CNS"
    elif len(documento) == 11:
        campo = "NUM_CPF"
    else:
        return None

    sql = f"""
        SELECT FIRST 1
            CNS, NUM_CPF, NOME, DTNASC, SEXO, RACA
        FROM CADCNS
        WHERE {campo} = ?
          AND NOME   IS NOT NULL AND TRIM(NOME)   <> ''
          AND DTNASC IS NOT NULL
          AND SEXO   IS NOT NULL AND TRIM(SEXO)   <> ''
          AND RACA   IS NOT NULL AND TRIM(RACA)   <> ''
    """

    try:
        con = conectar_firebird()
        cur = con.cursor()
        cur.execute(sql, (documento,))
        row = cur.fetchone()
        con.close()

        if not row:
            return None

        return {
            'cns':        row[0],
            'cpf':        row[1],
            'nome':       row[2],
            'nascimento': row[3],
            'sexo':       row[4],
            'raca':       row[5],
            'documento':  documento
        }

    except Exception as e:
        print(f"[BANCO] Erro ao buscar '{documento}': {e}")
        return None

# ==============================================================================
# 📦 PREPARAR LOTES  ←  lê o arquivo e chama buscar_paciente_no_banco pra cada linha
# ==============================================================================

def preparar_lotes(arq_leitura: str, callback=None) -> tuple[list, str]:
    if not os.path.exists(arq_leitura):
        return [], "Ficheiro não encontrado."

    with open(arq_leitura, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    lotes      = []
    lote_atual = None
    ignorados  = 0

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # --- Cabeçalho do lote (profissional + data) ---
        if "PROFISSIONAL:" in linha:
            if lote_atual:
                lotes.append(lote_atual)

            partes = linha.split('|')
            medico = partes[0].replace("PROFISSIONAL:", "").strip()
            data   = partes[1].replace("DATA:", "").strip()

            lote_atual = {
                'medico':    medico,
                'data':      data,
                'pacientes': [],   # aprovados no banco ✅
                'ignorados': []    # sem cadastro ou incompleto ⚠️
            }

        # --- Linha de documento (CPF ou CNS) ---
        elif lote_atual:
            paciente = buscar_paciente_no_banco(linha)  # ← aqui a mágica

            if paciente:
                lote_atual['pacientes'].append(paciente)
                if callback:
                    callback(f"✅ {paciente['nome']} ({linha})")
            else:
                ignorados += 1
                lote_atual['ignorados'].append(linha)
                if callback:
                    callback(f"⚠️  {linha} — sem cadastro ou campos obrigatórios vazios")

    if lote_atual:
        lotes.append(lote_atual)

    if callback:
        callback(f"\n📊 Lotes: {len(lotes)} | Ignorados: {ignorados}")

    return lotes, ""

# ==============================================================================
# 🤖 EXECUTOR DO ROBÔ  ←  recebe os pacientes já aprovados pelo banco
# ==============================================================================

pyautogui.FAILSAFE = True

def executar_pyautogui(medico, data_atend, procedimento, pacientes: list[dict], callback=None):
    data_limpa = "".join(c for c in data_atend if c.isdigit())
    total      = len(pacientes)

    for i, p in enumerate(pacientes, 1):
        if keyboard.is_pressed('esc'):
            if callback:
                callback("🛑 INTERROMPIDO PELO USUÁRIO (ESC)")
            break

        doc = p['documento']
        if callback:
            callback(f"🚀 {medico} | {i}/{total} | {p['nome']} | Doc: {doc}")

        try:
            pyautogui.write(doc)
            pyautogui.press('f7')
            time.sleep(1.0)

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
            time.sleep(1.0)

        except Exception as e:
            if callback:
                callback(f"❌ Erro em {doc}: {e}")
            continue