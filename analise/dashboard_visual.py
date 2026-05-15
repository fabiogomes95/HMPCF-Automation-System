"""
DASHBOARD_VISUAL.PY — Dashboard PNG + Relatório Top 20
========================================================
Gera um dashboard visual (PNG) com 4 gráficos e relatório
dos 20 pacientes que mais retornaram.

Uso direto:  python dashboard_visual.py
Via Eel:     analise_gerar_dashboard()
"""

import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from io import StringIO

pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))
if pasta_pai not in sys.path:
    sys.path.append(pasta_pai)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger


def gerar_dashboard() -> str:
    """
    Gera o dashboard PNG + relatório Top 20.
    Retorna uma string com o resultado (sucesso ou erro).
    Não usa input() — própria pra chamada via Eel.
    """
    caminho_db = os.path.join(pasta_pai, 'hospital.db')
    if not os.path.exists(caminho_db):
        msg = f"ERRO: Banco de dados nao encontrado em {caminho_db}"
        logger.error(msg)
        return msg

    conn = sqlite3.connect(caminho_db)
    query = """
        SELECT
            p.nome, p.sus, p.idade, p.sexo, p.bairro,
            a.data_atendimento, a.hora_atendimento, a.procedencia
        FROM atendimentos a
        JOIN pacientes p ON a.sus = p.sus
        WHERE a.sus != '' AND a.sus IS NOT NULL
    """
    df_mensal = pd.read_sql_query(query, conn)
    conn.close()

    if df_mensal.empty:
        return "Nao ha dados suficientes para gerar o Dashboard."

    buf = StringIO()
    _escrever_relatorio(df_mensal, buf)
    relatorio = buf.getvalue()
    logger.info(relatorio)

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Visao Geral de Atendimentos - HMPCF', fontsize=20, fontweight='bold')

    df_mensal['idade_num'] = pd.to_numeric(
        df_mensal['idade'].str.replace(' Anos', '', regex=False), errors='coerce'
    )
    sns.histplot(
        data=df_mensal, x='idade_num', hue='sexo', multiple='stack',
        palette={'M': '#3498db', 'F': '#e74c3c', 'MASCULINO': '#3498db', 'FEMININO': '#e74c3c'},
        kde=True, ax=axes[0, 0]
    )
    axes[0, 0].set_title('Distribuicao de Idade por Sexo', fontweight='bold')
    axes[0, 0].set_xlabel('Idade')
    axes[0, 0].set_ylabel('Quantidade de Pacientes')

    if 'bairro' in df_mensal.columns and not df_mensal['bairro'].isna().all():
        top_bairros = df_mensal['bairro'].value_counts().head(10)
        sns.barplot(
            x=top_bairros.values, y=top_bairros.index,
            palette='viridis', ax=axes[0, 1],
            hue=top_bairros.index, legend=False
        )
        axes[0, 1].set_title('Top 10 Bairros (Procedencia)', fontweight='bold')
        axes[0, 1].set_xlabel('Numero de Atendimentos')
    else:
        axes[0, 1].set_title('Dados de Bairro Indisponiveis', fontweight='bold')

    df_mensal['h'] = pd.to_numeric(df_mensal['hora_atendimento'].str.split(':').str[0], errors='coerce')
    sns.countplot(data=df_mensal, x='h', color='coral', ax=axes[1, 0])
    axes[1, 0].set_title('Picos de Horario na Recepcao', fontweight='bold')
    axes[1, 0].set_xlabel('Hora do Dia (0h - 23h)')
    axes[1, 0].set_ylabel('Volume de Entradas')

    df_mensal['dia'] = df_mensal['data_atendimento'].apply(
        lambda x: str(x).split('/')[-3] if '/' in str(x) else str(x).split('-')[-1]
    )
    dias_ordenados = sorted(df_mensal['dia'].dropna().unique())
    sns.countplot(
        data=df_mensal, x='dia', palette='Blues_d', hue='dia',
        legend=False, ax=axes[1, 1], order=dias_ordenados
    )
    axes[1, 1].set_title('Volume de Atendimentos por Dia', fontweight='bold')
    axes[1, 1].set_xlabel('Dia do Mes')
    axes[1, 1].set_ylabel('Total de Atendimentos')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    nome_arquivo = os.path.join(pasta_atual, 'dashboard_hmpcf.png')
    plt.savefig(nome_arquivo, dpi=300)
    plt.close()

    resultado = f"{relatorio}\nDashboard gerado: {nome_arquivo}"
    return resultado


def _escrever_relatorio(df, buf) -> None:
    """Escreve o relatório Top 20 num buffer de string."""
    buf.write("\n" + "=" * 60 + "\n")
    buf.write("TOP 20 PACIENTES COM MAIS ENTRADAS NO MES\n")
    buf.write("=" * 60 + "\n\n")

    df_valido = df[df['sus'].astype(str).str.strip() != '']
    df_valido = df_valido[df_valido['sus'].notna()]
    top_20_sus = df_valido['sus'].value_counts().head(20).index
    df_top20 = df_valido[df_valido['sus'].isin(top_20_sus)].copy()
    df_top20 = df_top20.sort_values(by=['nome', 'data_atendimento', 'hora_atendimento'])

    for pos, sus in enumerate(top_20_sus, 1):
        dados_p = df_top20[df_top20['sus'] == sus]
        if dados_p.empty:
            continue
        nome = dados_p['nome'].iloc[0]
        total = len(dados_p)
        buf.write(f"[{pos}] {nome}\n")
        buf.write(f"      SUS: {sus} | Total: {total} entradas\n")
        buf.write("      " + "-" * 40 + "\n")
        for _, row in dados_p.iterrows():
            buf.write(f"        -> Data: {row['data_atendimento']} as {row['hora_atendimento']}\n")
        buf.write("\n")


if __name__ == "__main__":
    logger.info(gerar_dashboard())
