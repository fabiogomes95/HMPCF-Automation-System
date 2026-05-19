import pyautogui
import time
import os
import keyboard
import firebirdsql
import ctypes

# ── IMPEDE QUE O WINDOWS SUSPENDA OU LIGUE PROTETOR DE TELA ──────────────────
# Enquanto o robô estiver rodando, o Windows não vai dormir nem bloquear a tela.
ES_CONTINUOUS      = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_keep_awake_handle = None

def manter_acordado(ativo: bool = True):
    global _keep_awake_handle
    if ativo:
        _keep_awake_handle = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
    else:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        _keep_awake_handle = None

# ==============================================================================
# 🔥 CONEXÃO FIREBIRD
# ==============================================================================

def conectar_firebird():
    return firebirdsql.connect(
        host='localhost',
        database=r'C:\BPA\BPAMAG.GDB',
        user='SYSDBA',
        password='masterkey',
        charset='WIN1252'
    )

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

    sql = f"SELECT FIRST 1 CNS, NUM_CPF, NOME FROM CADCNS WHERE {campo} = ?"

    try:
        con = conectar_firebird()
        cur = con.cursor()
        cur.execute(sql, (documento,))
        row = cur.fetchone()
        con.close()

        if not row:
            return None

        return {'documento': documento}

    except Exception as e:
        print(f"[BANCO] Erro ao buscar '{documento}': {e}")
        return None

# ==============================================================================
# 📦 PREPARAR LOTES  ←  lê o arquivo e chama buscar_paciente_no_banco pra cada linha
# ==============================================================================

def _buscar_na_ram(documento: str, base_pacientes: list[dict]) -> dict | None:
    for p in base_pacientes:
        if p['sus'] == documento or p['cpf'] == documento:
            return {'documento': documento}
    return None

def preparar_lotes(arq_leitura: str, base_pacientes: list[dict] | None = None, callback=None) -> tuple[list, str]:
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

        if "PROFISSIONAL:" in linha:
            if lote_atual:
                lotes.append(lote_atual)

            partes = linha.split('|')
            medico = partes[0].replace("PROFISSIONAL:", "").strip()
            data   = partes[1].replace("DATA:", "").strip()

            lote_atual = {
                'medico':    medico,
                'data':      data,
                'pacientes': [],
                'validados': [],
                'ignorados': []
            }

        elif lote_atual:
            if base_pacientes:
                paciente = _buscar_na_ram(linha, base_pacientes)
            else:
                paciente = buscar_paciente_no_banco(linha)

            if paciente:
                lote_atual['pacientes'].append(paciente)
                lote_atual['validados'].append(paciente)
                if callback:
                    callback(f"✅ ({linha})")
            else:
                ignorados += 1
                lote_atual['ignorados'].append(linha)
                if callback:
                    callback(f"⚠️  {linha} — sem cadastro")

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
    # Mantem Windows acordado durante a automacao
    manter_acordado(True)
    data_limpa = "".join(c for c in data_atend if c.isdigit())
    total      = len(pacientes)

    try:
        for i, p in enumerate(pacientes, 1):
            if keyboard.is_pressed('esc'):
                if callback:
                    callback("INTERROMPIDO PELO USUARIO (ESC)")
                break

            doc = p['documento']
            if callback:
                callback(f"{medico} | {i}/{total} | Doc: {doc}")

            try:
                pyautogui.write(doc)
                pyautogui.press('tab')
                time.sleep(1.0)
                pyautogui.press('f7')
                time.sleep(1.0)

                pyautogui.write(data_limpa)
                pyautogui.press('tab')

                pyautogui.write(procedimento)
                pyautogui.press('1')
                time.sleep(0.8)

                pyautogui.press(['tab', 'tab', 'tab'])
                pyautogui.write('2')
                time.sleep(0.8)

                pyautogui.press(['tab', 'tab'])
                pyautogui.press('enter')
                time.sleep(2.0)

            except pyautogui.FailSafeException:
                if callback:
                    callback("INTERROMPIDO (FAILSAFE - MOUSE NO CANTO)")
                break
            except Exception as e:
                if callback:
                    callback(f"Erro em {doc}: {e}")
                continue
    finally:
        # Restaura comportamento normal do Windows apos a automacao
        manter_acordado(False)