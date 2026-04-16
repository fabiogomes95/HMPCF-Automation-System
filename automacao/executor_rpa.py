# ==============================================================================
# 🤖 ROBÔ BPA: DIGITADOR INDEPENDENTE (VERSÃO FINAL CORRIGIDA)
# OBJETIVO: Lê o CSV, valida o SUS matematicamente e realiza a digitação RPA.
# SEGUE APENAS O ARQUIVO .CSV (Sem consulta ao banco de dados)
# ==============================================================================

import pyautogui  # Controle de teclado/mouse
import time       # Gerenciamento de pausas
import os         # Manipulação de arquivos
import sys        # Manipulação de caminhos do sistema

# --- 1. CONFIGURAÇÃO DE CAMINHO PARA O UTILS ---
# Como este script está em uma subpasta, subimos um nível para achar o utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importamos apenas o que o robô precisa para ser "seguro"
from utils import valida_cns, apenas_numeros

# --- 2. INTERFACE E COLETA DE DADOS ---
print("==================================================")
print("🤖 ROBÔ BPA: MODO VALIDAÇÃO + DIGITAÇÃO DIRETA  🤖")
print("==================================================\n")

# Dados que o BPA exige para cada folha/lote
data_atend = input("👉 1. Digite a DATA do atendimento (Ex: 15042026): ").strip()
procedimento = input("👉 2. Digite o CÓDIGO do procedimento (Ex: 0301010048): ").strip()

# Nome do arquivo de entrada (deve estar na mesma pasta deste script)
arq_diario = os.path.join(os.path.dirname(__file__), "pacientes.csv")

# Verificação defensiva: O arquivo existe?
if not os.path.exists(arq_diario):
    print(f"\n❌ ERRO: O arquivo '{arq_diario}' não foi encontrado na pasta.")
    exit()

pacientes_validados = []
rejeitados = []

# --- 3. FASE DE FILTRAGEM (O SEGURANÇA DO SISTEMA) ---
print(f"🔍 Analisando '{arq_diario}' para evitar erros no BPA...")

with open(arq_diario, 'r', encoding='utf-8') as f:
    for linha in f:
        # Limpa o número (remove espaços, pontos e traços) usando o utils
        sus_limpo = apenas_numeros(linha)
        
        if not sus_limpo:
            continue

        # Validação matemática oficial (Módulo 11) vinda do utils.py
        if valida_cns(sus_limpo):
            pacientes_validados.append(sus_limpo)
        else:
            # Se o número estiver errado, salvamos para o relatório de erro
            rejeitados.append(f"{sus_limpo} -> CNS INVÁLIDO (Erro matemático)")

# Se houver números errados no CSV, gera um log para você corrigir
if rejeitados:
    with open("sus_rejeitados.txt", "w", encoding='utf-8') as f:
        for r in rejeitados: f.write(r + "\n")
    print(f"⚠️ {len(rejeitados)} números foram REJEITADOS. Veja 'sus_rejeitados.txt'")

if not pacientes_validados:
    print("\n🛑 Nenhum paciente válido para digitar. O robô irá parar.")
    exit()

# --- 4. FASE DE AUTOMAÇÃO (ROBOTIC PROCESS AUTOMATION) ---
# O sistema BPA costuma aceitar lotes de até 99 registros por folha
lotes = [pacientes_validados[i:i + 99] for i in range(0, len(pacientes_validados), 99)]

print(f"✅ {len(pacientes_validados)} pacientes prontos para digitação.")

for i, lote in enumerate(lotes):
    print(f"\n📦 PROCESSANDO LOTE {i + 1} DE {len(lotes)} | Total: {len(lote)}")
    input("=> Vá ao BPA, abra uma folha NOVA e aperte ENTER aqui...")
    
    print("⏳ Você tem 5 segundos para clicar no primeiro campo de CNS do BPA...")
    time.sleep(5)
    
    for p in lote:
        # SEQUÊNCIA DE DIGITAÇÃO NO SISTEMA BPA
        pyautogui.write(p)             # Digita o número do SUS
        pyautogui.press('f7')          # Comando de pesquisa do sistema
        time.sleep(0.8)                # Pausa para o sistema carregar o cadastro
        
        pyautogui.write(data_atend)    # Preenche a data informada no início
        pyautogui.press('tab')
        
        pyautogui.write(procedimento)  # Preenche o código do procedimento
        pyautogui.press('1')           # Quantidade (Padrão 1)
        time.sleep(0.5)                # Pausa técnica para o Windows não travar
        
        # Navega até o Caráter de Atendimento
        pyautogui.press(['tab', 'tab', 'tab'])
        
        pyautogui.write('2')           # Código do caráter (Ex: Eletivo/Urgência)
        time.sleep(0.3)
        
        pyautogui.press('enter')       # Salva o registro na folha
        print(f"✅ Digitado: {p}")
        time.sleep(1.2)                # Espera o sistema "respirar" para o próximo

print("\n🎯 MISSÃO CUMPRIDA! O robô terminou a leitura do seu CSV.")