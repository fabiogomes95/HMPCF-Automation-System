"""
ANALISE_ANUAL_CSV.PY — Analisador de Frequência a partir de CSVs
=================================================================
Lê CSVs na pasta analise/ e gera PDF com Top 20 pacientes.

Uso direto:  python analise_anual_csv.py
Via Eel:     analise_analisar_csvs_para_pdf()
"""

import os
import csv
from io import StringIO
import pandas as pd
from datetime import datetime
import sys
from fpdf import FPDF

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros

LARGURA_COL = 88
MARGEM_ESQ = 10
ENTRE_COL = 8
MARGEM_INFERIOR = 20
Y_CABECALHO = 25
coluna_x = [MARGEM_ESQ, MARGEM_ESQ + LARGURA_COL + ENTRE_COL]


def _coluna_atual(pdf, col, y):
    if y > 297 - MARGEM_INFERIOR:
        col += 1
        if col > 1:
            pdf.add_page()
            col = 0
            y = Y_CABECALHO
        else:
            y = Y_CABECALHO
    return col, y


def _card(pdf, col, y, i, nome, dn, cpf, sus, total):
    col, y = _coluna_atual(pdf, col, y)
    x0 = coluna_x[col]
    alt = 40
    if y + alt > 297 - MARGEM_INFERIOR:
        col += 1
        if col > 1:
            pdf.add_page()
            col = 0
            y = Y_CABECALHO
        else:
            y = Y_CABECALHO
        x0 = coluna_x[col]
    pdf.set_xy(x0, y)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(180, 180, 180)
    pdf.rect(x0, y, LARGURA_COL, alt)
    pdf.set_xy(x0 + 2, y + 1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.multi_cell(LARGURA_COL - 4, 4, f"{i} - {nome}")
    pdf.set_xy(x0 + 2, pdf.get_y() + 1)
    pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(LARGURA_COL - 4, 4, f"NASC: {dn}")
    pdf.multi_cell(LARGURA_COL - 4, 4, f"CPF: {cpf}")
    pdf.multi_cell(LARGURA_COL - 4, 4, f"SUS: {sus}")
    pdf.set_font('Helvetica', 'B', 8)
    pdf.multi_cell(LARGURA_COL - 4, 4, f"TOTAL: {total} vez(es)")
    y = pdf.get_y() + 3
    return col, y


def formatar_cpf(cpf):
    c = apenas_numeros(cpf)
    if len(c) == 11:
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
    return "NAO INFORMADO"


def formatar_sus(sus):
    s = apenas_numeros(sus)
    if len(s) == 15:
        return f"{s[:3]} {s[3:7]} {s[7:11]} {s[11:]}"
    return "NAO INFORMADO"


def gerar_id_unico(row):
    cpf = apenas_numeros(row.get('cpf', ''))
    if len(cpf) == 11:
        return f"CPF_{cpf}"
    sus = apenas_numeros(row.get('sus', ''))
    if len(sus) == 15:
        return f"SUS_{sus}"
    nome_cru = str(row.get('nome', '')).upper().strip()
    nome = ''.join(c for c in nome_cru if c.isalnum())
    dn = apenas_numeros(row.get('dn', ''))
    if not nome or nome == 'NAN' or 'PLANTAO' in nome_cru or nome == 'NOME':
        return "IGNORAR"
    return f"NOME_{nome}_DN_{dn}"


def analisar_csvs_para_pdf():
    """
    Procura CSVs na pasta analise/, processa e gera PDF com Top 20.
    Retorna string com resultado.
    """
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    arquivos_csv = [
        os.path.join(pasta_atual, f)
        for f in os.listdir(pasta_atual)
        if f.lower().endswith('.csv')
    ]

    if not arquivos_csv:
        return "ERRO: Nenhum arquivo .csv encontrado na pasta."

    dfs = []
    colunas_oficiais = [
        'registro', 'nome', 'dn', 'idade', 'sexo', 'raca',
        'cidade', 'hora', 'cpf', 'sus', 'obs', 'endereco', 'tel'
    ]

    logger.info("INICIANDO LEITURA DOS CSVS...")
    for f in arquivos_csv:
        try:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    texto_csv = file.read()
            except UnicodeDecodeError:
                with open(f, 'r', encoding='latin1') as file:
                    texto_csv = file.read()

            delimitador = ';' if texto_csv.count(';') > texto_csv.count(',') else ','
            leitor = csv.reader(StringIO(texto_csv), delimiter=delimitador)
            dados_limpos = []
            for linha in leitor:
                if not linha:
                    continue
                while len(linha) < 13:
                    linha.append("")
                linha = linha[:13]
                dados_limpos.append(linha)

            df = pd.DataFrame(dados_limpos, columns=colunas_oficiais)
            if not df.empty and str(df.iloc[0]['nome']).strip().lower() == 'nome':
                df = df.iloc[1:].reset_index(drop=True)
            dfs.append(df)
            logger.info(f"Arquivo processado: {os.path.basename(f)} ({len(df)} registros)")
        except Exception as e:
            logger.error(f"Erro ao ler {os.path.basename(f)}: {e}")

    if not dfs:
        return "Nenhum dado valido pode ser extraido dos CSVs."

    df_geral = pd.concat(dfs, ignore_index=True)
    logger.info("Cruzando os dados e limpando ruidos...")
    df_geral['ID_UNICO'] = df_geral.apply(gerar_id_unico, axis=1)
    df_geral = df_geral[df_geral['ID_UNICO'] != "IGNORAR"]

    top_ids = df_geral['ID_UNICO'].value_counts().head(20).index
    df_top = df_geral[df_geral['ID_UNICO'].isin(top_ids)]

    logger.info("Gerando o PDF com fpdf2...")
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=False)

    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'HMPCF - AUDITORIA DE FREQUENCIA (CSV)', ln=True, align='C')
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, f'Top 20 Pacientes | Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', ln=True, align='C')
    pdf.ln(4)

    col = 0
    y = pdf.get_y()

    for i, id_paciente in enumerate(top_ids, start=1):
        dados_p = df_top[df_top['ID_UNICO'] == id_paciente]
        nomes_validos = dados_p.get('nome', pd.Series(dtype=str)).dropna()
        nome_exibicao = str(nomes_validos.iloc[0]).strip().upper() if not nomes_validos.empty else "NOME NAO INFORMADO"
        cpf_raw = dados_p.get('cpf', pd.Series(dtype=str)).dropna()
        cpf_exibicao = formatar_cpf(cpf_raw.iloc[0]) if not cpf_raw.empty else "NAO INFORMADO"
        sus_raw = dados_p.get('sus', pd.Series(dtype=str)).dropna()
        sus_exibicao = formatar_sus(sus_raw.iloc[0]) if not sus_raw.empty else "NAO INFORMADO"
        dn_raw = dados_p.get('dn', pd.Series(dtype=str)).dropna()
        dn_exibicao = str(dn_raw.iloc[0]).strip() if not dn_raw.empty else "NAO INFORMADA"
        total_entradas = len(dados_p)

        col, y = _card(pdf, col, y, i, nome_exibicao, dn_exibicao, cpf_exibicao, sus_exibicao, total_entradas)

    arquivo_pdf = os.path.join(pasta_atual, "RELATORIO_FREQUENCIA_CSV.pdf")
    pdf.output(arquivo_pdf)
    msg = f"SUCESSO! PDF gerado: {arquivo_pdf}"
    logger.info(msg)
    return msg


if __name__ == "__main__":
    logger.info("==================================================")
    logger.info("ANALISADOR DE FREQUENCIA DE PACIENTES (.CSV)")
    logger.info("==================================================")
    logger.info(analisar_csvs_para_pdf())
