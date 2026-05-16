"""
EXECUTOR_RPA.PY — Robô Digitador Automático (PyAutoGUI)
=========================================================
Esse é o coração do RPA — o robô que DIGITA automaticamente
os pacientes no sistema BPA do governo.

Como funciona:
1. O painel chama preparar_lotes() pra organizar os lotes
2. O usuário clica "Executar RPA" no frontend
3. O robô assume o controle do mouse/teclado
4. Digita paciente por paciente no sistema BPA
5. Se o usuário apertar ESC, o robô para na hora

SEGURANÇA:
- FAILSAFE = True: se o mouse for pro canto da tela, o robô para
- ESC: interrompe a execução imediatamente
- delay entre cada ação pra dar tempo do sistema processar
"""

import pyautogui
import time
import os
import sys
import keyboard
from typing import Callable

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger

# === TRAVA DE SEGURANÇA ===
# Se eu jogar o mouse no CANTO SUPERIOR ESQUERDO da tela,
# o PyAutoGUI levanta uma exceção e PARA TUDO.
# Isso é o "botão de pânico" físico do robô.
pyautogui.FAILSAFE = True


def preparar_lotes(arq_leitura: str, base_pacientes_ram: list[dict] | None = None) -> tuple[list[dict], str]:
    """
    Lê o arquivo de produção e organiza os lotes.
    
    O arquivo tem o formato:
        PROFISSIONAL: DR. FULANO | DATA: 13/04/2026
        123456789012345
        898765432109876
        ...
    
    Cada lote é um dicionário com:
        medico, data, pacientes, validados
    
    Parâmetros:
        arq_leitura: caminho do .txt de produção
        base_pacientes_ram: lista de dicts da RAM (pra validar)
    
    Retorna (lotes, erro).
    """
    if not os.path.exists(arq_leitura):
        return [], "Ficheiro nao encontrado."

    # --- PRÉ-CARREGA OS DOCUMENTOS VÁLIDOS DA RAM ---
    # Crio um SET pra busca ser instantânea (O(1) vs O(n))
    documentos_validos = set()
    if base_pacientes_ram:
        for p in base_pacientes_ram:
            if p.get('sus'):
                documentos_validos.add(p['sus'])
            if p.get('cpf'):
                documentos_validos.add(p['cpf'])

    with open(arq_leitura, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    lotes = []
    lote_atual = None

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # --- CABEÇALHO DO LOTE ---
        if "PROFISSIONAL:" in linha:
            # Salva o lote anterior antes de começar um novo
            if lote_atual:
                lotes.append(lote_atual)

            # Parse: "PROFISSIONAL: DR. FULANO | DATA: 13/04/2026"
            partes = linha.split('|')
            medico = partes[0].replace("PROFISSIONAL:", "").strip()
            data = partes[1].replace("DATA:", "").strip()

            lote_atual = {
                'medico': medico,
                'data': data,
                'pacientes': [],
                'validados': []
            }
        elif lote_atual:
            # --- PACIENTE DENTRO DO LOTE ---
            
            # 1. Se a gente carregou o banco (RAM), faz a peneira fina:
            if base_pacientes_ram:
                if linha in documentos_validos:
                    lote_atual['validados'].append(linha)
                    lote_atual['pacientes'].append(linha)
                else:
                    # ❌ IGNORA O PACIENTE: Ele não entra na lista do robô!
                    # Opcional: imprimir no log pra você saber quem ficou de fora
                    # logger.warning(f"Paciente ignorado (Não está no .GDB): {linha}")
                    continue 
            
            # 2. Se a gente não passou a RAM pra verificar, adiciona tudo direto:
            else:
                lote_atual['pacientes'].append(linha)

    if lote_atual:
        lotes.append(lote_atual)

    return lotes, ""


def executar_pyautogui(medico: str, data_atend: str, procedimento: str, pacientes: list[str], callback: Callable[[str], None] | None = None) -> None:
    """
    Executa a digitação automática no sistema BPA.
    
    Parâmetros:
        medico: nome do médico (só pra exibição)
        data_atend: data no formato DD/MM/AAAA
        procedimento: código do procedimento (ex: CODIGO_UNIDADE em config.py)
        pacientes: lista de strings (CPF ou SUS)
        callback: função pra atualizar o frontend
    
    Fluxo de teclas:
    1. Digita o documento (CPF/SUS)
    2. F7 → busca no sistema
    3. Digita a data
    4. Tab → procedimento
    5. Tab → digita código
    6. Enter → confirma
    
    O robô NÃO move o mouse — tudo é feito por TECLAS.
    """
    # Limpa a data: "13/04/2026" → "13042026"
    data_limpa = "".join([c for c in data_atend if c.isdigit()])

    total = len(pacientes)
    for i, p in enumerate(pacientes, 1):
        # --- VERIFICA INTERRUPÇÃO ---
        # Se o usuário apertar ESC, para tudo
        if keyboard.is_pressed('esc'):
            if callback:
                callback("INTERROMPIDO PELO USUARIO (ESC)")
            break

        if callback:
            callback(f"{medico} | {i}/{total} | Doc: {p}")

        try:
            # --- SEQUÊNCIA DE DIGITAÇÃO ---
            # Cada passo tem um delay pra dar tempo do sistema processar

            # Passo 1: Digita o CPF/SUS do paciente
            pyautogui.write(p)

            # Passo 2: Aperta F7 (atalho de busca do sistema BPA)
            pyautogui.press('f7')
            time.sleep(1.0)

            # Passo 3: Digita a data do atendimento (sem barras)
            pyautogui.write(data_limpa)
            pyautogui.press('tab')

            # Passo 4: Digita o código do procedimento
            pyautogui.write(procedimento)
            pyautogui.press('1')  # Código de atuação
            time.sleep(0.5)

            # Passo 5: Navega e confirma
            pyautogui.press(['tab', 'tab', 'tab'])
            pyautogui.write('2')  # Código complementar
            time.sleep(0.3)

            # Passo 6: Confirma o registro
            pyautogui.press(['tab', 'tab'])
            pyautogui.press('enter')
            time.sleep(0.7)

        except Exception as e:
            logger.error(f"Erro na digitacao: {e}")
            continue
