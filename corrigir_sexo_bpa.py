import pyautogui
import time
import os

# Configurações de Failsafe (Mova o mouse para o canto da tela para abortar)
pyautogui.FAILSAFE = True

print("==================================================")
print("🤖 ROBÔ INJETOR: MODO CONTROLE VIA TXT 🤖")
print("==================================================\n")

# Parâmetros fixos para a 'digitação fake' que salva o cadastro
data_atend = input("👉 1. Digite a DATA do atendimento (Ex: 15042026): ").strip()
procedimento = input("👉 2. Digite o CÓDIGO do procedimento (Ex: 0301010048): ").strip()

arquivo_lista = 'lista_correcao.txt'

if not os.path.exists(arquivo_lista):
    print(f"❌ Erro: O arquivo '{arquivo_lista}' não foi encontrado!")
    exit()

with open(arquivo_lista, 'r') as f:
    sus_lista = [linha.strip() for linha in f if linha.strip()]

print(f"📋 {len(sus_lista)} registros carregados do arquivo.")
input("=> Vá ao BPA, abra uma folha NOVA e aperte ENTER aqui...")
print("⏳ Iniciando em 5 segundos... Prepare o BPA!")
time.sleep(5)

for p in sus_lista:
    print(f"🚀 Processando: {p}")
    
    # 1. Digita SUS e define Sexo como 'I' antes do F7
    pyautogui.write(p)
    pyautogui.press('tab')      # 1 TAB após o SUS
    pyautogui.write('I')        # Força o Sexo 'I'
    pyautogui.press('f7')       # Processa
    time.sleep(1.2)             # Tempo para o BPA processar o cadastro
    
    # 2. Preenche o restante para validar a entrada na folha
    pyautogui.write(data_atend)
    pyautogui.press('tab')
    pyautogui.write(procedimento)
    pyautogui.press('1')
    time.sleep(0.5)
    
    # Navegação nos campos restantes
    pyautogui.press(['tab', 'tab', 'tab'])
    pyautogui.write('2')
    time.sleep(0.3)
    
    pyautogui.press(['tab', 'tab'])
    pyautogui.press('enter')
    
    print(f"✅ Finalizado: {p}")
    time.sleep(1.0)

print("\n🎉 Fim da lista de correção!")