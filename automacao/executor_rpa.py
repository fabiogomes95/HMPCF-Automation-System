# ==============================================================================
# 🤖 ROBÔ BPA: DIGITADOR INDEPENDENTE (VERSÃO COM ÍNDICE)
# OBJETIVO: Valida SUS, verifica cadastro no banco e faz o RPA.
# ==============================================================================

import pyautogui
import time
import os
import sys
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import valida_cns, apenas_numeros

print("==================================================")
print("🤖 ROBÔ BPA: MODO BANCO DE DADOS + DIGITAÇÃO  🤖")
print("==================================================\n")

data_atend = input("👉 1. Digite a DATA do atendimento (Ex: 15042026): ").strip()
procedimento = input("👉 2. Digite o CÓDIGO do procedimento (Ex: 0301010048): ").strip()

caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')
arq_diario = os.path.join(os.path.dirname(__file__), "pacientes.csv")

if not os.path.exists(arq_diario):
    print(f"\n❌ ERRO: O arquivo '{arq_diario}' não foi encontrado.")
    exit()

pacientes_validados = []
rejeitados = []

print(f"🔍 Cruzando dados com '{caminho_db}'...")

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # Lê as linhas mantendo a estrutura para pegar o número exato da linha
    with open(arq_diario, 'r', encoding='utf-8') as f:
        linhas_hoje = f.readlines()

    for num_linha, linha_texto in enumerate(linhas_hoje, start=1):
        sus_limpo = apenas_numeros(linha_texto)
        if not sus_limpo: 
            continue

        # Passo 1: Validação Matemática (usa a função do utils.py)
        if not valida_cns(sus_limpo):
            rejeitados.append(f"Linha {num_linha:03d} | {sus_limpo} -> CNS INVÁLIDO (Matemático/Digitação)")
            continue

        # Passo 2: Verificação de Existência no Banco de Dados (CORRIGIDO PARA 'sus')
        cursor.execute("SELECT sus FROM pacientes WHERE sus = ?", (sus_limpo,))
        
        if cursor.fetchone():
            pacientes_validados.append(sus_limpo)
        else:
            rejeitados.append(f"Linha {num_linha:03d} | {sus_limpo} -> NÃO CADASTRADO NO BANCO LOCAL")

    conn.close()
except sqlite3.Error as e:
    print(f"❌ ERRO AO ACESSAR O BANCO: {e}")
    exit()

# Relatório de Erros detalhado
if rejeitados:
    with open("sus_rejeitados.txt", "w", encoding='utf-8') as f:
        for r in rejeitados: f.write(r + "\n")
    print(f"⚠️ {len(rejeitados)} problemas encontrados. Veja o arquivo 'sus_rejeitados.txt' para saber as linhas exatas.")

if not pacientes_validados:
    print("\n🛑 Nenhum paciente apto para digitação. O robô parou.")
    exit()

# --- FASE DE AUTOMAÇÃO ---
lotes = [pacientes_validados[i:i + 99] for i in range(0, len(pacientes_validados), 99)]
print(f"✅ {len(pacientes_validados)} pacientes confirmados e prontos.")

for i, lote in enumerate(lotes):
    print(f"\n📦 LOTE {i + 1}/{len(lotes)}")
    input("=> Vá ao BPA, abra a folha e aperte ENTER...")
    time.sleep(5)
    
    for p in lote:
        pyautogui.write(p)
        pyautogui.press('f7')
        time.sleep(1.0) 
        
        pyautogui.write(data_atend)
        pyautogui.press('tab')
        pyautogui.write(procedimento)
        pyautogui.press('1')
        time.sleep(0.5)
        
        pyautogui.press(['tab', 'tab', 'tab'])
        pyautogui.write('2')
        time.sleep(0.3)
        
        pyautogui.press(['tab', 'tab'])
        pyautogui.press('enter')
        print(f"✅ Digitado: {p}")
        time.sleep(1.2)

print("\n🎯 MISSÃO CUMPRIDA!")