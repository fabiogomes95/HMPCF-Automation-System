"""
CONVERTER_CSV.PY — Conversor de CSVs Antigos para TXT BPA
==========================================================
Antes do sistema atual, a recepção usava um formato CSV de 13 colunas
(REGISTRO, NOME, DN, IDADE, SEXO, RACA, CIDADE, HORARIO, CPF, SUS,
 OBS, ENDERECO, TEL).

Esse script lê esses CSVs antigos e converte pro mesmo formato
posicional do BPA que o exportar_bpa.py produz.

O diferencial: ele faz parse INTELIGENTE do endereço separando
rua, número e bairro mesmo quando vem tudo bagunçado.
"""

import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros, remove_accents
from config import CNS_PROFISSIONAL, CBO_CODIGO, FOLHA_CODIGO, SEQ_PROFISSIONAL

E_CBO = CBO_CODIGO
F_FOLHA = FOLHA_CODIGO
G_SEQ = SEQ_PROFISSIONAL
H_CNS_PROF = CNS_PROFISSIONAL


def processar_csv_antigo(caminho_csv="", caminho_salvar=""):
    """
    Converte um CSV antigo (13 colunas) pro formato TXT BPA.
    
    Parâmetros:
        caminho_csv: caminho do arquivo CSV a ser convertido
        caminho_salvar: onde salvar o .txt gerado
    
    Retorna mensagem com: total convertido, barrados, log de erros.
    """
    if not caminho_csv:
        return "Erro: Nenhum arquivo CSV informado."

    # --- LEITURA DO CSV ---
    # Tento UTF-8 primeiro, se falhar, latin1
    try:
        df = pd.read_csv(
            caminho_csv, dtype=str, encoding='utf-8',
            on_bad_lines='skip'
        )
    except Exception:
        df = pd.read_csv(
            caminho_csv, dtype=str, encoding='latin1',
            on_bad_lines='skip'
        )

    linhas_bpa = []
    lista_erros = []

    for index, row in df.iterrows():
        try:
            # Mínimo de 13 colunas
            if len(row) < 13:
                continue

            # --- NOME ---
            nome_bruto = str(row.iloc[1]).strip()
            if nome_bruto.upper() in ['NAN', '']:
                continue
            nome = remove_accents(nome_bruto)

            # --- SUS (CNS) ---
            raw_sus = str(row.iloc[9]).split('.')[0]
            cns = apenas_numeros(raw_sus)
            if len(cns) != 15:
                lista_erros.append(
                    f"LINHA {index + 2} | {nome[:30]} | "
                    f"ERRO: SUS ({cns}) incompleto ou ausente."
                )
                continue

            # --- DATA DE NASCIMENTO ---
            dn_raw = str(row.iloc[2]).strip()
            data_f = None
            if '-' in dn_raw:
                parts = dn_raw.split('-')
                if len(parts) >= 3:
                    data_f = (
                        f"{parts[0][:4].zfill(4)}"
                        f"{parts[1][:2].zfill(2)}"
                        f"{parts[2][:2].zfill(2)}"
                    )
            elif '/' in dn_raw:
                parts = dn_raw.split('/')
                if len(parts) >= 3:
                    data_f = (
                        f"{parts[2][:4].zfill(4)}"
                        f"{parts[1][:2].zfill(2)}"
                        f"{parts[0][:2].zfill(2)}"
                    )
            if not data_f or len(data_f) != 8:
                data_f = "19900101"

            # --- SEXO ---
            sexo_raw = str(row.iloc[4]).strip().upper()
            sexo = sexo_raw[:1] if sexo_raw[:1] in ['M', 'F'] else 'I'

            # --- PARSE DO ENDEREÇO ---
            # Formato esperado: "RUA EXEMPLO, 123. BAIRRO CENTRO"
            endereco_raw = str(row.iloc[11]).strip()
            if endereco_raw.upper() == "NAN":
                endereco_raw = ""

            rua = ""
            numero = "S/N"
            # Pego o bairro da coluna 6 (CIDADE/BAIRRO)
            bairro = str(row.iloc[6]).strip()
            if bairro.upper() == "NAN":
                bairro = ""

            if endereco_raw:
                if ',' in endereco_raw:
                    # Separo pela PRIMEIRA vírgula
                    partes_virgula = endereco_raw.split(',', 1)
                    rua = partes_virgula[0].strip()
                    resto = partes_virgula[1].strip()
                    if '.' in resto:
                        # Separo pelo ponto
                        partes_ponto = resto.split('.', 1)
                        numero = partes_ponto[0].strip()
                        bairro_extraido = partes_ponto[1].strip()
                        if bairro_extraido:
                            bairro = bairro_extraido
                    else:
                        numero = resto
                else:
                    rua = endereco_raw

            # Padronizo e trunco
            rua_f = remove_accents(rua).ljust(30)[:30]
            num_f = remove_accents(numero).ljust(5)[:5]
            if not num_f.strip():
                num_f = "S/N".ljust(5)
            bairro_f = remove_accents(bairro).ljust(30)[:30]

            # --- TELEFONE ---
            tel_digits = apenas_numeros(str(row.iloc[12]))
            telefone_f = "".ljust(11)
            if 8 <= len(tel_digits) <= 11:
                if len(tel_digits) <= 9:
                    tel_digits = "84" + tel_digits
                telefone_f = tel_digits.ljust(11)[:11]

            # --- LINHA BPA ---
            nome_f = nome.ljust(30)[:30]
            line = (
                f"{cns}{nome_f}{data_f}{sexo}"
                f"{E_CBO}{F_FOLHA}{G_SEQ}    "
                f"{H_CNS_PROF}{rua_f}          "
                f"{num_f}{bairro_f}{telefone_f}"
            )
            linhas_bpa.append(line)

        except Exception as e_linha:
            lista_erros.append(
                f"LINHA {index + 2} | ERRO INESPERADO: {e_linha}"
            )

    # --- SALVA O ARQUIVO TXT ---
    if not caminho_salvar:
        caminho_salvar = "BPA_PLANILHA_ANTIGA.txt"

    with open(caminho_salvar, 'w', encoding='cp1252', errors='replace') as out_f:
        for linha in linhas_bpa:
            out_f.write(linha + '\n')

    # --- RELATÓRIO ---
    mensagem = (
        f"Conversao Finalizada!\n"
        f"Pacientes no BPA: {len(linhas_bpa)}\n"
        f"Barrados (Sem SUS): {len(lista_erros)}"
    )
    if lista_erros:
        arquivo_erros = caminho_salvar.replace(
            '.txt', '_PACIENTES_SEM_CADASTRO.txt'
        )
        with open(arquivo_erros, 'w', encoding='utf-8') as log_f:
            log_f.write("--- RELATORIO DE PACIENTES BARRADOS ---\n")
            log_f.write(f"Total Sucessos: {len(linhas_bpa)}\n")
            log_f.write(f"Total Barrados: {len(lista_erros)}\n")
            log_f.write("----------------------------------------\n\n")
            for e in lista_erros:
                log_f.write(e + '\n')
        mensagem += f"\nLog de erros: {arquivo_erros}"

    return mensagem


if __name__ == "__main__":
    csv_path = input("Caminho do CSV: ").strip()
    logger.info(processar_csv_antigo(csv_path))
