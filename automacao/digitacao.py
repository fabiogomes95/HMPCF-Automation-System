"""
DIGITACAO.PY — Módulo Digitador Manual | Busca na RAM e Lotes de 99
=====================================================================
Esse módulo ajuda a DIGITAÇÃO MANUAL dos pacientes no sistema BPA.

Funcionalidades:
1. buscar_pacientes_memoria() — busca ultrarrápida na RAM (não no Firebird)
2. criar_cabecalho_producao() — adiciona cabeçalho de médico+lote
3. adicionar_ficha_producao() — adiciona paciente ao lote com quebra automática de 99

A "quebra de 99" é uma regra de negócio: o sistema BPA do governo
só aceita lotes de NO MÁXIMO 99 pacientes por vez. Então quando
o lote atinge 99, esse módulo DUPLICA automaticamente o cabeçalho
pra criar um novo lote.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros


def buscar_pacientes_memoria(termo, base_pacientes_ram):
    """
    Busca pacientes na RAM (lista em memória) em vez de consultar o Firebird.
    
    Por que na RAM? O Firebird tá em rede e é LENTO. Quando o usuário
    digita um nome no campo de busca, cada tecla dispara uma busca.
    Se fosse no banco, demoraria segundos.
    Na RAM, é instantâneo.
    
    Parâmetros:
        termo: o que o usuário digitou (nome, SUS ou CPF)
        base_pacientes_ram: lista de dicts carregada do Firebird
    
    Retorna: lista de até 50 pacientes que correspondem ao termo.
    """
    if not termo:
        # Se não digitou nada, mostra os 50 primeiros
        return base_pacientes_ram[:50]

    termo = termo.upper().strip()
    resultados = []

    # Varre a RAM na velocidade da luz
    for p in base_pacientes_ram:
        if termo in p['nome'] or termo in p['sus'] or termo in p['cpf']:
            resultados.append(p)
            # Limite de 50 resultados pra não travar o frontend HTML
            if len(resultados) == 50:
                break

    return resultados


def criar_cabecalho_producao(caminho_completo, medico, data):
    """
    Adiciona um cabeçalho de lote no arquivo de produção.
    
    Formato: "PROFISSIONAL: DR. FULANO | DATA: 13/04/2026"
    
    Esse formato é lido pelo executor_rpa.py pra saber
    qual médico e data pertencem a cada lote.
    """
    try:
        with open(caminho_completo, 'a', encoding='utf-8') as f:
            f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")
        return True
    except Exception as e:
        print(f"Erro ao criar cabecalho manual: {e}")
        return False


def adicionar_ficha_producao(caminho_completo, documento):
    """
    Adiciona o documento (CPF/SUS) de um paciente no lote atual.
    
    REGRA DOS 99:
    Se o lote atual já tem 99 pacientes, o script DUPLICA
    automaticamente o último cabeçalho ("PROFISSIONAL: ...")
    antes de adicionar o paciente 100.
    
    Isso cria um novo lote sem perder a referência do médico/data.
    
    Como descobre quantos pacientes tem no lote atual:
    - Lê o arquivo de TRÁS PRA FRENTE
    - Conta as linhas até encontrar o último cabeçalho
    """
    doc_limpo = apenas_numeros(documento).strip()

    try:
        pacientes_no_lote = 0
        ultimo_cabecalho = ""

        # --- LEITURA REVERSA (de baixo pra cima) ---
        # Quero saber quantos pacientes tem no lote ATUAL
        if os.path.exists(caminho_completo):
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()

            for linha in reversed(linhas):
                linha_limpa = linha.strip()
                if not linha_limpa:
                    continue
                # Se achou o cabeçalho, parou
                if linha_limpa.startswith("PROFISSIONAL:"):
                    ultimo_cabecalho = linha_limpa
                    break
                else:
                    pacientes_no_lote += 1

        # --- ADICIONA O PACIENTE ---
        with open(caminho_completo, 'a', encoding='utf-8') as f:
            # Se estourou a cota, duplica o cabeçalho
            if pacientes_no_lote >= 99 and ultimo_cabecalho:
                f.write(f"\n{ultimo_cabecalho}\n")

            f.write(f"{doc_limpo}\n")

        return True

    except Exception as e:
        print(f"Erro ao salvar ficha manual: {e}")
        return False
