# ==============================================================================
# 🤖 ROBÔ BPA: DIGITADOR INDEPENDENTE (VERSÃO COM ÍNDICE)
# OBJETIVO: Valida SUS, verifica cadastro no banco e faz o RPA.
# ==============================================================================

import pyautogui
import time
import os
import sys
import sqlite3
import re
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import valida_cns, apenas_numeros

print("==================================================")
print("🤖 ROBÔ BPA: MODO BANCO DE DADOS + DIGITAÇÃO  🤖")
print("==================================================\n")

data_atend = input("👉 1. Digite a DATA do atendimento (Ex: 15042026): ").strip()

print("\n👉 2. Escolha o PROCEDIMENTO:")
print("   [1] Médico     (0301060029)")
print("   [2] Enfermeiro (0301010048)")
opcao_proc = input("=> Digite a opção (1 ou 2): ").strip()

if opcao_proc == '1':
    procedimento = "0301060029"
elif opcao_proc == '2':
    procedimento = "0301010048"
else:
    print("❌ Opção inválida. O robô foi encerrado.")
    exit()

# PERGUNTA NOVA ADICIONADA AQUI
nome_profissional = input("\n👉 3. Digite o NOME do profissional (Ex: Dr. Carlos): ").strip().upper()
if not nome_profissional:
    nome_profissional = "NÃO INFORMADO"

caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')
arq_diario = os.path.join(os.path.dirname(__file__), "pacientes.csv")

if not os.path.exists(arq_diario):
    print(f"\n❌ ERRO: O arquivo '{arq_diario}' não foi encontrado.")
    exit()

pacientes_validados = []
rejeitados = []

print(f"\n🔍 Cruzando dados com '{caminho_db}'...")

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # Descobre o nome da coluna de data de nascimento dinamicamente no seu banco
    coluna_data = None
    cursor.execute("PRAGMA table_info(pacientes)")
    colunas = [info[1].lower() for info in cursor.fetchall()]
    for col in ['data_nascimento', 'data_nasc', 'nascimento', 'dt_nasc', 'dtnasc']:
        if col in colunas:
            coluna_data = col
            break

    # Lê as linhas mantendo a estrutura para pegar o número exato da linha
    with open(arq_diario, 'r', encoding='utf-8') as f:
        linhas_hoje = f.readlines()

    ano_atual = datetime.now().year

    for num_linha, linha_texto in enumerate(linhas_hoje, start=1):
        sus_limpo = apenas_numeros(linha_texto)
        if not sus_limpo: 
            continue

        # Passo 1: Validação Matemática (usa a função do utils.py)
        if not valida_cns(sus_limpo):
            rejeitados.append(f"Linha {num_linha:03d} | {sus_limpo} -> CNS INVÁLIDO (Matemático/Digitação)")
            continue

        # Passo 2: Verificação de Existência no Banco e Limite Humano de Idade
        if coluna_data:
            cursor.execute(f"SELECT sus, {coluna_data} FROM pacientes WHERE sus = ?", (sus_limpo,))
            resultado = cursor.fetchone()
            
            if resultado:
                data_nasc = str(resultado[1]).strip() if resultado[1] else ""
                
                # Extrai o ano da string (ex: 10/12/1125 pega o 1125)
                match_ano = re.search(r'\b(\d{4})\b', data_nasc)
                if match_ano:
                    ano = int(match_ano.group(1))
                    # Trava de Segurança Humana (1900 até o ano atual)
                    if ano < 1900 or ano > ano_atual:
                        rejeitados.append(f"Linha {num_linha:03d} | {sus_limpo} -> DATA EXTRAPOLADA ({data_nasc})")
                        continue
                
                pacientes_validados.append(sus_limpo)
            else:
                rejeitados.append(f"Linha {num_linha:03d} | {sus_limpo} -> NÃO CADASTRADO NO BANCO LOCAL")
        else:
            # Fallback seguro caso seu banco não tenha a coluna de data
            cursor.execute("SELECT sus FROM pacientes WHERE sus = ?", (sus_limpo,))
            if cursor.fetchone():
                pacientes_validados.append(sus_limpo)
            else:
                rejeitados.append(f"Linha {num_linha:03d} | {sus_limpo} -> NÃO CADASTRADO NO BANCO LOCAL")

    conn.close()
except sqlite3.Error as e:
    print(f"❌ ERRO AO ACESSAR O BANCO: {e}")
    exit()

# ======================================================================
# NOVO SISTEMA DE LOG ACUMULATIVO (NÃO APAGA OS ANTERIORES)
# ======================================================================
if rejeitados:
    arquivo_log = "historico_rejeitados.txt"
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # O 'a' no open significa Append (adicionar no fim do arquivo)
    with open(arquivo_log, "a", encoding='utf-8') as f:
        f.write(f"\n[{data_hora}] ==================================================\n")
        f.write(f"PROFISSIONAL: {nome_profissional}\n")
        f.write(f"DATA ATEND. : {data_atend} | PROCEDIMENTO: {procedimento}\n")
        f.write("----------------------------------------------------------------\n")
        for r in rejeitados: 
            f.write(r + "\n")
            
    print(f"⚠️ {len(rejeitados)} problemas encontrados. Veja o log acumulado em '{arquivo_log}'.")

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