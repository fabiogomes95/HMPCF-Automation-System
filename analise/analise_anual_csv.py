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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros


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

    print("\nINICIANDO LEITURA DOS CSVS...")
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
            print(f"Arquivo processado: {os.path.basename(f)} ({len(df)} registros)")
        except Exception as e:
            print(f"Erro ao ler {os.path.basename(f)}: {e}")

    if not dfs:
        return "Nenhum dado valido pode ser extraido dos CSVs."

    df_geral = pd.concat(dfs, ignore_index=True)
    print("\nCruzando os dados e limpando ruidos...")
    df_geral['ID_UNICO'] = df_geral.apply(gerar_id_unico, axis=1)
    df_geral = df_geral[df_geral['ID_UNICO'] != "IGNORAR"]

    top_ids = df_geral['ID_UNICO'].value_counts().head(20).index
    df_top = df_geral[df_geral['ID_UNICO'].isin(top_ids)]

    print("Gerando o PDF...")
    pacientes_html = ""

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

        pacientes_html += f"""
        <div class="patient-card">
            <div class="patient-name">{i} - {nome_exibicao}</div>
            <div class="patient-info"><b>NASCIMENTO:</b> {dn_exibicao}</div>
            <div class="patient-info"><b>CPF:</b> {cpf_exibicao}</div>
            <div class="patient-info"><b>SUS:</b> {sus_exibicao}</div>
            <div class="patient-info"><b>TOTAL DE ENTRADAS:</b> {total_entradas} vez(es)</div>
        </div>"""

    html_template = f"""
    <html><head><meta charset="UTF-8"><style>
        @page {{ size: A4; margin: 1.5cm; background-color: #ffffff; }}
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
        .patient-info {{ margin-bottom: 3px; color: #333; font-size: 10pt; }}
    </style></head><body>
        <div class="header">
            <h1>HMPCF - AUDITORIA DE FREQUENCIA (CSV)</h1>
            <p>Top 20 Pacientes | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        <div class="container">{pacientes_html}</div>
    </body></html>"""

    from weasyprint import HTML
    arquivo_pdf = os.path.join(pasta_atual, "RELATORIO_FREQUENCIA_CSV.pdf")
    HTML(string=html_template).write_pdf(arquivo_pdf)
    msg = f"SUCESSO! PDF gerado: {arquivo_pdf}"
    print(msg)
    return msg


if __name__ == "__main__":
    print("==================================================")
    print("ANALISADOR DE FREQUENCIA DE PACIENTES (.CSV)")
    print("==================================================\n")
    print(analisar_csvs_para_pdf())
