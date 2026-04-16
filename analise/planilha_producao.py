# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO DE RELATÓRIOS MENSAL
# Desenvolvido para analisar o banco SQLite e gerar relatórios em Excel.
# Versão Integrada com utils.py (Padronização de Dados)
# =========================================================================
import pandas as pd
import sqlite3
import os
import sys

# Bibliotecas do OpenPyXL para pintura e formatação
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# --- CONEXÃO COM A RAIZ (Para achar o utils.py) ---
# Como este script está em 'analise_dados/', subimos um nível (..)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents

def gerar_relatorio_final():
    # =====================================================================
    # 1. LOCALIZAÇÃO E LEITURA DO BANCO DE DADOS
    # =====================================================================
    # Caminho dinâmico para achar o banco na pasta raiz
    caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')

    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: O banco de dados não foi encontrado em: {caminho_db}")
        return

    try:
        conn = sqlite3.connect(caminho_db)
        
        # Query otimizada (Usa as mesmas regras de JOIN do dashboard)
        query = """
        SELECT DISTINCT
            p.nome, p.dn, p.idade, p.sexo, p.raca, p.cidade, 
            a.data_atendimento, a.hora_atendimento,
            p.cpf, p.sus, p.endereco, p.numero, p.bairro, p.tel, 
            a.procedencia
        FROM pacientes p
        JOIN atendimentos a ON (p.cpf = a.cpf AND p.cpf != '') OR (p.sus = a.sus AND p.sus != '')
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # O EXTERMINADOR DE CLONES: Apaga duplicatas exatas de Nome/Data/Hora
        df = df.drop_duplicates(subset=['nome', 'data_atendimento', 'hora_atendimento'])
        
    except Exception as e:
        print(f"❌ Erro ao ler o banco: {e}")
        return

    # =====================================================================
    # 2. INTELIGÊNCIA TEMPORAL E "REGRA DA MADRUGADA"
    # =====================================================================
    df['dt_entrada'] = pd.to_datetime(
        df['data_atendimento'] + ' ' + df['hora_atendimento'], 
        errors='coerce'
    )

    df = df.dropna(subset=['dt_entrada', 'nome'])
    df = df[df['nome'].str.strip() != '']

    # Se o atendimento foi antes das 07:00, conta no plantão do dia anterior
    df['Data_Logica'] = df['dt_entrada'].apply(
        lambda x: (x - pd.Timedelta(days=1)).date() if x.hour < 7 else x.date()
    )

    df['Mes_Ref'] = pd.to_datetime(df['Data_Logica']).dt.strftime('%m-%Y')

    # =====================================================================
    # 3. INTERAÇÃO COM O USUÁRIO (ESCOLHA DO MÊS)
    # =====================================================================
    meses = sorted(df['Mes_Ref'].unique())
    print(f"\n📅 Meses detectados no sistema: {meses}")
    escolha = input("👉 Digite o mês que deseja gerar (Ex: 04-2026): ").strip()

    df_mes = df[df['Mes_Ref'] == escolha].copy()

    if df_mes.empty:
        print(f"❌ Nenhum atendimento encontrado para {escolha}.")
        return

    # =====================================================================
    # 4. ORGANIZAÇÃO DOS DADOS E LIMPEZA (PANDAS + UTILS)
    # =====================================================================
    colunas = ['Nº', 'Nome do Paciente', 'Data Nasc.', 'Idade', 'Sexo', 'Raça/Cor', 
               'Município', 'Hora', 'CPF', 'Cartão SUS', 'Procedência', 'Endereço', 'Telefone']
    
    dados_finais = []
    df_mes = df_mes.sort_values('dt_entrada')
    
    grupos = df_mes.groupby([
        'Data_Logica', 
        df_mes['dt_entrada'].dt.hour.apply(lambda x: 'DIURNO' if 7<=x<19 else 'NOTURNO')
    ], sort=False)

    print(f"🧹 Formatando dados de {escolha} para o padrão Excel...")

    for (data, turno), grupo in grupos:
        # Cabeçalho do Plantão
        dados_finais.append({'Nº': f"PLANTÃO {turno} - {data.strftime('%d/%m/%Y')}"})
        
        for i, (_, r) in enumerate(grupo.iterrows(), 1):
            
            # --- USO DO UTILS.PY PARA LIMPEZA ---
            nome_limpo = remove_accents(r['nome'])
            cidade_limpa = remove_accents(r['cidade'])
            bairro_limpo = remove_accents(r['bairro'])
            rua_limpa = remove_accents(r['endereco'])
            
            # Formata CPF e SUS para serem apenas números (evita erro de fórmula no Excel)
            cpf_f = apenas_numeros(r['cpf'])
            sus_f = apenas_numeros(r['sus'])
            
            # Procedência
            proc = remove_accents(str(r['procedencia'])) if r['procedencia'] else ''
            if proc == 'NORMAL': proc = ''
            
            dn_br = pd.to_datetime(r['dn']).strftime('%d/%m/%Y') if r['dn'] and str(r['dn']) != 'nan' else ""
            
            # Endereço montado e limpo
            end_f = f"{rua_limpa}, {str(r['numero'] or '').strip()} - {bairro_limpo}"

            dados_finais.append({
                'Nº': i, 'Nome do Paciente': nome_limpo, 'Data Nasc.': dn_br,
                'Idade': r['idade'], 'Sexo': r['sexo'], 'Raça/Cor': r['raca'], 
                'Município': cidade_limpa, 'Hora': r['dt_entrada'].strftime('%H:%M'),
                'CPF': cpf_f, 'Cartão SUS': sus_f, 
                'Procedência': proc, 'Endereço': end_f, 'Telefone': r['tel']
            })

    # =====================================================================
    # 5. GERAÇÃO DO ARQUIVO EXCEL (OPENPYXL)
    # =====================================================================
    nome_arq = "Relatorio_Producao_HMPCF.xlsx"

    if os.path.exists(nome_arq):
        wb = load_workbook(nome_arq)
        if escolha in wb.sheetnames: del wb[escolha]
        ws = wb.create_sheet(title=escolha)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = escolha

    ws.append(colunas)

    for linha in dados_finais:
        ws.append(list(linha.values()))

    # --- ESTILIZAÇÃO FINAL ---
    fill_not = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    fill_diu = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")
    font_h = Font(color="FFFFFF", bold=True)
    center = Alignment(horizontal="center", vertical="center")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    for row in range(1, ws.max_row + 1):
        primeira_celula = str(ws.cell(row=row, column=1).value)
        
        if "PLANTÃO" in primeira_celula:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=13)
            cor = fill_not if "NOTURNO" in primeira_celula else fill_diu
            for col in range(1, 14):
                c = ws.cell(row=row, column=col)
                c.fill, c.font, c.alignment = cor, font_h, center
        else:
            for col in range(1, 14):
                c = ws.cell(row=row, column=col)
                c.border = border
                if col in [5, 8, 10]: c.alignment = center

    # Ajuste de largura das colunas
    dims = {'A':6, 'B':35, 'C':12, 'D':6, 'E':6, 'F':12, 'G':15, 'H':8, 'I':15, 'J':18, 'K':15, 'L':40, 'M':15}
    for col, width in dims.items():
        ws.column_dimensions[col].width = width

    ws.freeze_panes = 'A2'
    wb.save(nome_arq)
    print(f"✅ Relatório '{escolha}' gerado com sucesso em '{nome_arq}'!")

if __name__ == "__main__":
    gerar_relatorio_final()