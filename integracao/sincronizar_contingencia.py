"""
SINCRONIZAR_CONTINGENCIA.PY — Sincronizador de Planilhas Offline
=================================================================
Esse é o "salva-vidas" do sistema. Quando a recepção fica offline
(sem energia/sem internet) e anota os pacientes em planilhas manuais
de contingência, esse script consegue ler esses dados bagunçados.

O DIFERENCIAL:
- Usa REGEX INTELIGENTE pra "caçar" CPF, SUS, Nome e Data de
  Nascimento — independente da coluna onde foram digitados
- Detecta automaticamente se o CSV usa ',' ou ';'
- Se o paciente já existe no banco com SUS corrompido,
  atualiza com o SUS válido da planilha
- Gera logs separados de PROCESSADOS e ERROS
"""

import csv
import re
import os
import sqlite3
from datetime import datetime
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import (
    apenas_numeros, remove_accents, parse_endereco_fixed, valida_cns
)


def sincronizar_contingencia(caminho_csv=""):
    """
    Processa um CSV de contingência e sincroniza com o SQLite.
    
    Parâmetros:
        caminho_csv: caminho do CSV manual da recepção
    
    O que ele faz:
    1. Varre cada linha do CSV
    2. Usa regex pra achar CPF, SUS, Nome e Data de Nascimento
    3. Se o CPF já existe no banco:
       - Se o SUS do banco for inválido, ATUALIZA com o SUS da planilha
    4. Se o CPF não existe no banco:
       - Insere novo paciente (se tiver SUS válido e data de nascimento)
    5. Gera logs detalhados
    """
    if not caminho_csv:
        return "Erro: Nenhum arquivo CSV informado."

    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(pasta_script, '..', 'hospital.db')

    try:
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()

        # --- CARREGA TODOS OS PACIENTES DO BANCO PRA MEMÓRIA ---
        # Crio um dicionário: {cpf_limpo: (cpf_original, sus_limpo)}
        cursor.execute("SELECT cpf, sus FROM pacientes")
        mapa_banco = {
            apenas_numeros(row[0]): (row, apenas_numeros(row[1]))
            for row in cursor.fetchall() if row
        }

        adicionados = 0    # Novos pacientes inseridos
        atualizados = 0    # SUS corrigido
        ignorados = 0      # Já tinham SUS OK
        processados_log = []
        erros_log = []

        # --- DETECÇÃO AUTOMÁTICA DO SEPARADOR ---
        # Leio os primeiros bytes pra decidir
        with open(caminho_csv, 'r', encoding='latin-1', errors='replace') as f:
            content = f.read(1024)
            separador = ';' if content.count(';') > content.count(',') else ','

        # --- PROCESSAMENTO LINHA A LINHA ---
        with open(caminho_csv, 'r', encoding='latin-1', errors='replace') as f:
            reader = csv.reader(f, delimiter=separador)

            for i, row in enumerate(reader):
                linha_num = i + 1
                if len(row) < 5:
                    continue

                # --- EXTRAÇÃO DO NOME ---
                # Procuro a primeira coluna que:
                # - Tem mais de 5 caracteres
                # - NÃO contém números
                # - NÃO é cabeçalho (EXTREMOZ, PACIENTE, NOME, REGISTRO)
                nome_raw = next((
                    c for c in row
                    if len(c) > 5
                    and not re.search(r'\d', c)
                    and c.upper() not in [
                        "EXTREMOZ", "PACIENTE", "NOME", "REGISTRO"
                    ]
                ), "")
                if not nome_raw:
                    continue

                # --- EXTRAÇÃO DO CPF ---
                # Regex que acha CPF mesmo com pontuação
                cpf_plan = apenas_numeros(next((
                    re.search(
                        r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', c
                    ).group(0) for c in row
                    if re.search(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', c)
                ), ""))

                # --- EXTRAÇÃO DO SUS ---
                # Procuro uma coluna com exatamente 15 dígitos
                # começando com 1, 2, 7, 8 ou 9
                sus_plan = apenas_numeros(next((
                    c for c in row
                    if len(apenas_numeros(c)) == 15
                    and apenas_numeros(c)[0] in '12789'
                ), ""))

                id_paciente = (
                    f"NOME: {nome_raw[:30].ljust(30)} | "
                    f"CPF: {cpf_plan.ljust(11)}"
                )
                if not cpf_plan and not sus_plan:
                    continue

                # --- CASO 1: CPF JÁ EXISTE NO BANCO ---
                if cpf_plan in mapa_banco:
                    cpf_orig_banco, sus_banco_limpo = mapa_banco[cpf_plan]
                    # Só atualizo se o SUS do banco for inválido
                    if len(sus_banco_limpo) < 15:
                        if valida_cns(sus_plan):
                            cursor.execute(
                                "UPDATE pacientes SET sus = ? WHERE cpf = ?",
                                (sus_plan, cpf_orig_banco)
                            )
                            atualizados += 1
                            processados_log.append(
                                f"[ATUALIZADO] {id_paciente} | "
                                f"NOVO SUS: {sus_plan}"
                            )
                        else:
                            erros_log.append(
                                f"Linha {linha_num:04d} | "
                                f"{id_paciente} | "
                                f"MOTIVO: SUS Invalido ({sus_plan})"
                            )
                    else:
                        ignorados += 1
                    continue

                # --- CASO 2: NOVO PACIENTE ---
                # Só insiro se tiver SUS válido
                if not valida_cns(sus_plan):
                    erros_log.append(
                        f"Linha {linha_num:04d} | "
                        f"{id_paciente} | "
                        f"MOTIVO: SUS Invalido para novo cadastro"
                    )
                    continue

                # --- EXTRAÇÃO DA DATA DE NASCIMENTO ---
                data_banco = ""
                for col in row:
                    # Regex pra achar datas tipo: 01/02/1990, 01-02-90, etc
                    m = re.search(
                        r'(\d{2})[^\d]*(\d{2})[^\d]*(\d{4}|\d{2})', col
                    )
                    if m and len(col) < 15:
                        dia, mes, ano = m.groups()
                        if len(ano) == 2:
                            ano = "20" + ano if int(ano) < 30 else "19" + ano
                        data_banco = f"{ano}-{mes}-{dia}"
                        break

                if not data_banco:
                    erros_log.append(
                        f"Linha {linha_num:04d} | "
                        f"{id_paciente} | "
                        f"MOTIVO: Data de Nascimento nao encontrada"
                    )
                    continue

                # Parse do endereço (se existir)
                rua, num, bairro = parse_endereco_fixed(
                    row[-1] if len(row) > 5 else ""
                )

                # --- INSERE NO BANCO ---
                cursor.execute('''
                    INSERT OR REPLACE INTO pacientes
                    (cpf, sus, nome, dn, sexo, raca,
                     endereco, numero, bairro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cpf_plan, sus_plan, remove_accents(nome_raw),
                    data_banco, " ", "PARDA", rua, num, bairro
                ))

                adicionados += 1
                processados_log.append(
                    f"[NOVO]       {id_paciente} | SUS: {sus_plan}"
                )

        conn.commit()
        conn.close()

        # --- GERA LOGS EM ARQUIVO ---
        pasta_planilha = os.path.dirname(caminho_csv)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        if processados_log:
            with open(
                os.path.join(
                    pasta_planilha, f"PROCESSADOS_{timestamp}.txt"
                ),
                'w', encoding='utf-8'
            ) as f:
                f.write(
                    "--- PACIENTES PROCESSADOS COM SUCESSO ---\n\n"
                )
                for item in processados_log:
                    f.write(item + "\n")

        if erros_log:
            with open(
                os.path.join(
                    pasta_planilha,
                    f"ERROS_SINCRONIZACAO_{timestamp}.txt"
                ),
                'w', encoding='utf-8'
            ) as f:
                f.write(
                    "--- PACIENTES COM ERRO "
                    "(CORRIGIR NA PLANILHA) ---\n\n"
                )
                for item in erros_log:
                    f.write(item + "\n")

        msg = (
            f"Sincronizacao Finalizada!\n"
            f"Novos: {adicionados}\n"
            f"Atualizados: {atualizados}\n"
            f"Ja OK: {ignorados}"
        )
        if erros_log:
            msg += f"\nAtencao: {len(erros_log)} erros encontrados."
        return msg

    except Exception as e:
        return f"Erro no banco: {e}"


if __name__ == "__main__":
    csv_path = input("Caminho do CSV de contingencia: ").strip()
    logger.info(sincronizar_contingencia(csv_path))
