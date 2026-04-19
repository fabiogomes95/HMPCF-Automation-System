# ==============================================================================
# ROBÔ DE CORREÇÃO PONTUAL (RPA)
# ==============================================================================
# OBJETIVO:
# Este robô lê a "lista_correcao.txt" gerada pelo auditor e conserta
# os dados diretamente no software do governo simulando o uso do teclado.
# ==============================================================================

import pyautogui # Biblioteca Mestra de RPA (Controla mouse e teclado)
import time      # Para criar delays e esperar o computador pensar
import os

# Trava de Segurança: Se o robô ficar louco, jogar o mouse no canto da tela cancela tudo!
pyautogui.FAILSAFE = True 

print("==================================================")
print("🤖 ROBÔ INJETOR: MODO CONTROLE VIA TXT 🤖")
print("==================================================\n")

# ==============================================================================
# 1. PARÂMETROS E PREPARAÇÃO
# ==============================================================================
# Como o objetivo é apenas corrigir o cadastro, usamos dados genéricos para salvar a ficha
data_atend = input("👉 1. Digite a DATA do atendimento (Ex: 15042026): ").strip()
procedimento = input("👉 2. Digite o CÓDIGO do procedimento (Ex: 0301010048): ").strip()

arquivo_lista = 'lista_correcao.txt'

if not os.path.exists(arquivo_lista):
    print(f"❌ Erro: O arquivo '{arquivo_lista}' não foi encontrado!")
    exit()

# Abre o arquivo e lê todos os SUS com problemas
with open(arquivo_lista, 'r') as f:
    sus_lista = [linha.strip() for linha in f if linha.strip()]

print(f"📋 {len(sus_lista)} registros carregados do arquivo.")
input("=> Vá ao BPA, abra uma folha NOVA e aperte ENTER aqui...")

print("⏳ Iniciando em 5 segundos... Prepare o BPA!")
time.sleep(5)

# ==============================================================================
# 2. EXECUÇÃO DO FLUXO DO ROBÔ
# ==============================================================================
for p in sus_lista:
    print(f"🚀 Processando: {p}")
    
    # 1º Passo: Digita SUS e define Sexo como 'I' antes do sistema governamental travar
    pyautogui.write(p)
    pyautogui.press('tab')      # Aperta a tecla TAB para pular de campo
    pyautogui.write('I')        # Força o Sexo 'I' na caixinha correta
    pyautogui.press('f7')       # F7 é a tecla de atalho do BPA para processar a busca
    
    time.sleep(1.2)             # Aguarda 1 segundo e meio para o software do governo pensar
    
    # 2º Passo: Preenche o restante dos dados obrigatórios para validar a folha
    pyautogui.write(data_atend)
    pyautogui.press('tab')
    
    pyautogui.write(procedimento)
    pyautogui.press('1')        # Digita '1' na quantidade
    time.sleep(0.5)
    
    # Navegação final nos campos restantes (Saltos com TAB)
    pyautogui.press(['tab', 'tab', 'tab'])
    pyautogui.write('2')
    time.sleep(0.3)
    
    pyautogui.press(['tab', 'tab'])
    pyautogui.press('enter')    # Aperta Enter para confirmar e salvar a correção!
    
    print(f"✅ Finalizado: {p}")
    time.sleep(1.0) 

print("\n🎉 Fim da lista de correção!")