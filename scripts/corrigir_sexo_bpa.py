"""
CORRIGIR_SEXO_BPA.PY — Robô RPA Corretor de Sexo no Sistema BPA
=================================================================
Esse robô lê a lista_correcao.txt gerada pelo auditor_bpa.py
e CORRIGE o campo Sexo diretamente no sistema BPA do governo.

Como funciona:
1. O auditor_bpa.py gerou uma lista de SUS com sexo inválido
2. O usuário informa a data e o procedimento
3. O robô assume o teclado e, pra cada SUS:
   - Digita o SUS
   - Força o sexo 'I' (Indefinido)
   - Preenche data e procedimento
   - Confirma com Enter

SEGURANÇA:
- FAILSAFE = True (mouse no canto = para tudo)
- O usuário tem 5 segundos pra posicionar o cursor no BPA
- ESC não funciona aqui (diferente do executor_rpa.py)

Uso: python scripts/corrigir_sexo_bpa.py
"""

import pyautogui
import time
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger

# Trava de segurança: mouse no canto da tela = PARA TUDO
pyautogui.FAILSAFE = True

logger.info("==================================================")
logger.info("ROBO INJETOR: MODO CONTROLE VIA TXT")
logger.info("==================================================")

# --- PARÂMETROS ---
data_atend = input(
    "1. Digite a DATA do atendimento (Ex: 15042026): "
).strip()
procedimento = input(
    "2. Digite o CODIGO do procedimento (Ex: 0301010048): "
).strip()

arquivo_lista = 'lista_correcao.txt'

if not os.path.exists(arquivo_lista):
    logger.error(f"Erro: O arquivo '{arquivo_lista}' nao foi encontrado!")
    exit()

# Carrega a lista de SUS pra corrigir
with open(arquivo_lista, 'r') as f:
    sus_lista = [linha.strip() for linha in f if linha.strip()]

logger.info(f"{len(sus_lista)} registros carregados do arquivo.")
input(
    "=> Va ao BPA, abra uma folha NOVA e aperte ENTER aqui..."
)

logger.info("Iniciando em 5 segundos... Prepare o BPA!")
time.sleep(5)

# --- EXECUÇÃO DO FLUXO ---
for p in sus_lista:
    logger.info(f"Processando: {p}")
    pyautogui.write(p)
    pyautogui.press('tab')

    # 2. Força o sexo 'I' (Indefinido)
    pyautogui.write('I')
    pyautogui.press('f7')  # Busca no sistema
    time.sleep(1.2)

    # 3. Preenche data
    pyautogui.write(data_atend)
    pyautogui.press('tab')

    # 4. Preenche procedimento
    pyautogui.write(procedimento)
    pyautogui.press('1')  # Quantidade
    time.sleep(0.5)

    # 5. Navega e confirma
    pyautogui.press(['tab', 'tab', 'tab'])
    pyautogui.write('2')
    time.sleep(0.3)

    pyautogui.press(['tab', 'tab'])
    pyautogui.press('enter')  # Salva

    logger.info(f"Finalizado: {p}")
    time.sleep(1.0)

logger.info("Fim da lista de correcao!")
