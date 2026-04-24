# ==============================================================================
# 📄 GERADOR DE AUDITORIA PERIÓDICA EM PDF (HMPCF) - LADO A LADO
# ==============================================================================
# OBJETIVO:
# 1. Escolha de período via terminal (1, 3 ou 6 meses).
# 2. Conexão direta com hospital.db usando DISTINCT para evitar clones do Excel.
# 3. Geração de PDF com layout Side-by-Side (2 colunas) dos Top 20 pacientes.
# ==============================================================================

import os
import sqlite3
import pandas as pd
import sys
from weasyprint import HTML
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURAÇÃO DE ROTAS E AMBIENTE
# ==============================================================================
pasta_atual = os.path.dirname(os.path.abspath(__file__))
# Sobe um nível para encontrar o banco na raiz
caminho_db = os.path.abspath(os.path.join(pasta_atual, '..', 'hospital.db'))

def calcular_data_inicio(meses):
    """Calcula a data de corte retroativa com base nos meses escolhidos."""
    hoje = datetime.now()
    return (hoje - timedelta(days=meses * 30)).strftime('%Y-%m-%d')

def gerar_auditoria_pdf():
    print("==================================================")
    print("📑 GERADOR DE RELATÓRIO DE AUDITORIA (PDF)")
    print("==================================================\n")

    # ESCOLHA DO PERÍODO
    print("Escolha o período do relatório:")
    print("[1] Mensal (Últimos 30 dias)")
    print("[3] Trimestral (Últimos 90 dias)")
    print("[6] Semestral (Últimos 180 dias)")
    
    opcao = input("\n👉 Digite a opção (1, 3 ou 6): ").strip()
    
    if opcao not in ['1', '3', '6']:
        print("🛑 Opção inválida. Operação cancelada.")
        return
    
    qtd_meses = int(opcao)
    data_limite = calcular_data_inicio(qtd_meses)
    
    nomes_periodo = {'1': 'MENSAL', '3': 'TRIMESTRAL', '6': 'SEMESTRAL'}
    titulo_periodo = nomes_periodo[opcao]
    arquivo_pdf = os.path.join(pasta_atual, f"RELATORIO_AUDITORIA_{titulo_periodo}.pdf")

    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: Banco de dados não encontrado em: {caminho_db}")
        return

    print(f"\n⏳ Conectando ao banco e buscando dados desde {data_limite}...")

    try:
        conn = sqlite3.connect(caminho_db)
        
        # 🛡️ SQL BLINDADO: Traz apenas dados do período e aplica DISTINCT 
        # para ignorar "duplos cliques" da recepção (mesmo SUS, data e hora)
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
            print("🛑 Nenhum atendimento encontrado no período selecionado.")
            return

        # 2. IDENTIFICANDO OS TOP 20 PACIENTES
        # Conta as ocorrências limpas de cada SUS e pega os 20 maiores
        top_sus = df['sus'].value_counts().head(20).index
        df_top20 = df[df['sus'].isin(top_sus)].sort_values(by=['nome', 'data_atendimento', 'hora_atendimento'])

        print("🏗️ Montando estrutura visual do PDF...")

        pacientes_html = ""

        # 3. GERAÇÃO DOS CARTÕES HTML
        for sus in top_sus:
            dados_p = df_top20[df_top20['sus'] == sus]
            if dados_p.empty: continue
            
            nome = str(dados_p['nome'].iloc[0]).strip()
            cpf = str(dados_p['cpf'].iloc[0]).strip() if dados_p['cpf'].iloc[0] else "NÃO INFORMADO"
            total = len(dados_p)

            linhas_tempo = ""
            for i, (_, row) in enumerate(dados_p.iterrows(), start=1):
                d_br = row['data_atendimento']
                try:
                    if '-' in str(d_br):
                        d_br = datetime.strptime(d_br, '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    pass # Mantém como está se der erro de conversão
                
                linhas_tempo += f"<div><span class='idx'>[{i:02d}]</span> ➜ Data: {d_br} às {row['hora_atendimento']}</div>"

            pacientes_html += f"""
            <div class="patient-card">
                <div class="patient-name">👤 {nome}</div>
                <div class="patient-info">💳 <b>CPF:</b> {cpf}</div>
                <div class="patient-info">🏥 <b>SUS:</b> {sus}</div>
                <div class="patient-info">🔄 <b>TOTAL DE ENTRADAS:</b> {total} vez(es)</div>
                <div class="history-title">📅 LINHA DO TEMPO:</div>
                <div class="history-list">
                    {linhas_tempo}
                </div>
            </div>
            """

        # 4. TEMPLATE HTML E CSS COMPLETO
        html_template = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ 
                    size: A4; 
                    margin: 1.5cm; 
                    @bottom-right {{
                        content: "Página " counter(page) " de " counter(pages);
                        font-family: Arial, sans-serif;
                        font-size: 8pt;
                        color: #7f8c8d;
                    }}
                }}
                body {{ font-family: 'Segoe UI', sans-serif; color: #333; background: #ffffff; margin: 0; }}
                .header {{ text-align: center; background-color: #2c3e50; color: white; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 18pt; letter-spacing: 1px; }}
                .header p {{ margin: 5px 0 0 0; font-size: 10pt; color: #bdc3c7; }}
                
                /* Mágica do Layout em Colunas */
                .container {{ column-count: 2; column-gap: 1.5cm; width: 100%; }}
                
                .patient-card {{ 
                    break-inside: avoid; /* Evita cortar paciente no meio da página */
                    page-break-inside: avoid;
                    background-color: #ffffff;
                    border-left: 5px solid #3498db;
                    border-radius: 4px;
                    padding: 12px; 
                    margin-bottom: 15px; 
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    font-size: 9pt;
                }}
                .patient-name {{ font-weight: bold; font-size: 11pt; text-transform: uppercase; margin-bottom: 8px; color: #2c3e50; border-bottom: 1px solid #ecf0f1; padding-bottom: 4px; }}
                .patient-info {{ margin-bottom: 3px; color: #555; }}
                .history-title {{ font-weight: bold; margin-top: 8px; margin-bottom: 4px; color: #7f8c8d; font-size: 8.5pt; }}
                .history-list {{ margin-left: 5px; padding-left: 8px; border-left: 2px solid #ecf0f1; line-height: 1.4; color: #444; }}
                .idx {{ color: #777; font-family: monospace; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 HMPCF - AUDITORIA {titulo_periodo}</h1>
                <p>Top 20 Pacientes - Dados Higienizados (Sem Duplicatas) | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            <div class="container">
                {pacientes_html}
            </div>
        </body>
        </html>
        """

        # 5. GERA O PDF
        HTML(string=html_template).write_pdf(arquivo_pdf)
        print(f"\n✅ SUCESSO! Relatório PDF gerado e otimizado.")
        print(f"📁 Arquivo salvo em: {arquivo_pdf}")

    except Exception as e:
        print(f"\n❌ ERRO FATAL AO PROCESSAR PDF: {e}")

if __name__ == "__main__":
    gerar_auditoria_pdf()