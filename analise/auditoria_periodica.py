"""
AUDITORIA_PERIODICA.PY — PDF de Auditoria (Top 20 Pacientes)
==============================================================
Gera PDF profissional em DUAS COLUNAS com Top 20 pacientes.

Uso direto:  python auditoria_periodica.py
Via Eel:     analise_gerar_auditoria_periodo("1")  / "3" / "6"
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_raiz = os.path.abspath(os.path.join(pasta_atual, '..'))
caminho_db = os.path.join(pasta_raiz, 'hospital.db')


def calcular_data_inicio(meses):
    hoje = datetime.now()
    data_calculada = hoje - timedelta(days=meses * 30)
    return data_calculada.strftime('%Y-%m-%d')


def gerar_auditoria_periodo(opcao):
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
        print(msg)
        return msg

    print(f"Buscando dados a partir de {data_limite}...")

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

        print("Montando blocos de informacao para o PDF...")
        pacientes_html = ""

        for sus in top_sus:
            dados_p = df_top20[df_top20['sus'] == sus]
            if dados_p.empty:
                continue
            nome = str(dados_p['nome'].iloc[0]).strip()
            cpf = str(dados_p['cpf'].iloc[0]).strip() if dados_p['cpf'].iloc[0] else "NAO INFORMADO"
            total_entradas = len(dados_p)
            linhas_tempo = ""
            for i, (_, row) in enumerate(dados_p.iterrows(), start=1):
                d_br = row['data_atendimento']
                try:
                    if '-' in str(d_br):
                        d_br = datetime.strptime(d_br, '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    pass
                linhas_tempo += (
                    f"<div><span class='idx'>[{i:02d}]</span> "
                    f"-> Data: {d_br} as {row['hora_atendimento']}</div>"
                )
            pacientes_html += f"""
            <div class="patient-card">
                <div class="patient-name">{nome}</div>
                <div class="patient-info"><b>CPF:</b> {cpf}</div>
                <div class="patient-info"><b>SUS:</b> {sus}</div>
                <div class="patient-info"><b>TOTAL DE ENTRADAS:</b> {total_entradas} vez(es)</div>
                <div class="history-title">LINHA DO TEMPO:</div>
                <div class="history-list">{linhas_tempo}</div>
            </div>"""

        html_template = f"""
        <html><head><meta charset="UTF-8"><style>
            @page {{ size: A4; margin: 1.5cm; background-color: #ffffff;
                @bottom-right {{ content: "Pagina " counter(page) " de " counter(pages);
                    font-family: Arial, sans-serif; font-size: 8pt; color: #555; }} }}
            body {{ font-family: 'Segoe UI', sans-serif; color: #000; background: #ffffff; margin: 0; }}
            .header {{ text-align: center; background-color: #ffffff; color: #000; padding: 10px 0;
                border-bottom: 2px solid #000; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; font-size: 16pt; letter-spacing: 1px; font-weight: bold; }}
            .header p {{ margin: 5px 0 0 0; font-size: 10pt; color: #555; }}
            .container {{ column-count: 2; column-gap: 1.5cm; width: 100%; }}
            .patient-card {{ break-inside: avoid; page-break-inside: avoid; background-color: #ffffff;
                border: 1px solid #ccc; border-left: 4px solid #333; border-radius: 4px; padding: 12px;
                margin-bottom: 15px; font-size: 9pt; }}
            .patient-name {{ font-weight: bold; font-size: 11pt; text-transform: uppercase;
                margin-bottom: 8px; color: #000; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
            .patient-info {{ margin-bottom: 3px; color: #333; }}
            .history-title {{ font-weight: bold; margin-top: 8px; margin-bottom: 4px; color: #555; font-size: 8.5pt; }}
            .history-list {{ margin-left: 5px; padding-left: 8px; border-left: 2px solid #ddd;
                line-height: 1.4; color: #222; }}
            .idx {{ color: #555; font-family: monospace; font-weight: bold; }}
        </style></head><body>
            <div class="header">
                <h1>HMPCF - AUDITORIA {titulo_periodo}</h1>
                <p>Top 20 Pacientes - Dados Higienizados (Distinct) |
                Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            <div class="container">{pacientes_html}</div>
        </body></html>"""

        try:
            from weasyprint import HTML
        except Exception:
            return "ERRO: Biblioteca WeasyPrint requer GTK3 instalado. Baixe de: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
        HTML(string=html_template).write_pdf(arquivo_pdf)
        msg = f"SUCESSO! PDF gerado: {arquivo_pdf}"
        print(msg)
        return msg

    except Exception as e:
        msg = f"ERRO FATAL AO PROCESSAR PDF: {e}"
        print(msg)
        return msg


if __name__ == "__main__":
    print("Escolha o periodo retroativo do relatorio:")
    print("[1] Mensal (Ultimos 30 dias)")
    print("[3] Trimestral (Ultimos 90 dias)")
    print("[6] Semestral (Ultimos 180 dias)")
    opcao = input("\nDigite a opcao (1, 3 ou 6): ").strip()
    print(gerar_auditoria_periodo(opcao))
