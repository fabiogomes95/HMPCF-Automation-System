"""
AUDITORIA_PERIODICA.PY — PDF de Auditoria (Top 20 Pacientes)
==============================================================
Gera PDF profissional em DUAS COLUNAS com Top 20 pacientes.

Uso direto:  python auditoria_periodica.py
Via Eel:     analise_gerar_auditoria_periodo("1")  / "3" / "6"
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger

pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_raiz = os.path.abspath(os.path.join(pasta_atual, '..'))
caminho_db = os.path.join(pasta_raiz, 'hospital.db')

LARGURA_COL = 88
MARGEM_ESQ = 10
ENTRE_COL = 8
MARGEM_INFERIOR = 20
Y_CABECALHO = 25

coluna_x = [MARGEM_ESQ, MARGEM_ESQ + LARGURA_COL + ENTRE_COL]


def _coluna_atual(pdf, col: int, y: float) -> tuple[int, float]:
    if y > 297 - MARGEM_INFERIOR:
        col += 1
        if col > 1:
            pdf.add_page()
            col = 0
            y = Y_CABECALHO
        else:
            y = Y_CABECALHO
    return col, y


def _card_paciente(pdf, col: int, y: float, nome: str, cpf: str, sus: str, total: int, linhas_tempo: list[str]) -> tuple[int, float]:
    col, y = _coluna_atual(pdf, col, y)
    x0 = coluna_x[col]
    alt = 12 + len(linhas_tempo) * 5
    if alt < 25:
        alt = 25
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
    w = LARGURA_COL
    pdf.rect(x0, y, w, alt)
    pdf.set_xy(x0 + 2, y + 1)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.multi_cell(w - 4, 5, nome)
    pdf.set_xy(x0 + 2, pdf.get_y() + 1)
    pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(w - 4, 4, f"CPF: {cpf}")
    pdf.multi_cell(w - 4, 4, f"SUS: {sus}")
    pdf.set_font('Helvetica', 'B', 8)
    pdf.multi_cell(w - 4, 4, f"TOTAL: {total} vez(es)")
    pdf.set_font('Helvetica', '', 7)
    for t in linhas_tempo:
        pdf.multi_cell(w - 4, 4, t)
    y = pdf.get_y() + 3
    return col, y


def calcular_data_inicio(meses: int) -> str:
    hoje = datetime.now()
    data_calculada = hoje - timedelta(days=meses * 30)
    return data_calculada.strftime('%Y-%m-%d')


def gerar_auditoria_periodo(opcao: str) -> str:
    """
    Gera PDF de auditoria para o período escolhido.
    opcao: "1" (mensal), "3" (trimestral) ou "6" (semestral).
    Retorna string com resultado.
    """
    if opcao not in ['1', '3', '6']:
        return "Opcao invalida. Use '1', '3' ou '6'."

    qtd_meses = int(opcao)
    data_limite = calcular_data_inicio(qtd_meses)
    nomes_periodo = {'1': 'MENSAL', '3': 'TRIMESTRAL', '6': 'SEMESTRAL'}
    titulo_periodo = nomes_periodo[opcao]
    arquivo_pdf = os.path.join(pasta_atual, f"RELATORIO_AUDITORIA_{titulo_periodo}.pdf")

    if not os.path.exists(caminho_db):
        msg = f"ERRO: Banco nao encontrado em:\n{caminho_db}"
        logger.error(msg)
        return msg

    logger.info(f"Buscando dados a partir de {data_limite}...")

    try:
        conn = sqlite3.connect(caminho_db)
        query = """
            SELECT DISTINCT
                p.nome, p.cpf, p.sus,
                a.data_atendimento, a.hora_atendimento
            FROM pacientes p
            JOIN atendimentos a ON p.sus = a.sus
            WHERE a.sus != '' AND a.sus IS NOT NULL
              AND date(a.data_atendimento) >= date(?)
            ORDER BY a.data_atendimento DESC, a.hora_atendimento DESC
        """
        df = pd.read_sql_query(query, conn, params=(data_limite,))
        conn.close()

        if df.empty:
            return "Nenhum atendimento encontrado no periodo."

        top_sus = df['sus'].value_counts().head(20).index
        df_top20 = df[df['sus'].isin(top_sus)].sort_values(
            by=['nome', 'data_atendimento', 'hora_atendimento']
        )

        logger.info("Montando PDF com fpdf2...")
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=False)

        def cabecalho():
            pdf.set_font('Helvetica', 'B', 14)
            pdf.cell(0, 8, f'HMPCF - AUDITORIA {titulo_periodo}', ln=True, align='C')
            pdf.set_font('Helvetica', '', 8)
            pdf.cell(0, 4, f'Top 20 Pacientes | Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', ln=True, align='C')
            pdf.ln(4)

        pdf.add_page()
        cabecalho()
        col = 0
        y = pdf.get_y()

        for sus in top_sus:
            dados_p = df_top20[df_top20['sus'] == sus]
            if dados_p.empty:
                continue
            nome = str(dados_p['nome'].iloc[0]).strip()
            cpf = str(dados_p['cpf'].iloc[0]).strip() if dados_p['cpf'].iloc[0] else "NAO INFORMADO"
            total_entradas = len(dados_p)
            linhas_tempo = []
            for i, (_, row) in enumerate(dados_p.iterrows(), start=1):
                d_br = row['data_atendimento']
                try:
                    if '-' in str(d_br):
                        d_br = datetime.strptime(d_br, '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    pass
                linhas_tempo.append(f"[{i:02d}] Data: {d_br} as {row['hora_atendimento']}")
            col, y = _card_paciente(pdf, col, y, nome, cpf, sus, total_entradas, linhas_tempo)

        pdf.output(arquivo_pdf)
        msg = f"SUCESSO! PDF gerado: {arquivo_pdf}"
        logger.info(msg)
        return msg

    except Exception as e:
        msg = f"ERRO FATAL AO PROCESSAR PDF: {e}"
        logger.error(msg)
        return msg


if __name__ == "__main__":
    logger.info("Escolha o periodo retroativo do relatorio:")
    logger.info("[1] Mensal (Ultimos 30 dias)")
    logger.info("[3] Trimestral (Ultimos 90 dias)")
    logger.info("[6] Semestral (Ultimos 180 dias)")
    opcao = input("\nDigite a opcao (1, 3 ou 6): ").strip()
    logger.info(gerar_auditoria_periodo(opcao))
