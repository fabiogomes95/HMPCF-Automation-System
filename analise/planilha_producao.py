# ==============================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO DE RELATÓRIOS (EXCEL)
# ==============================================================================
# OBJETIVO:
# Este script atua como o setor administrativo automatizado. Ele lê o banco,
# extermina duplicações físicas, aplica as regras de plantão hospitalar 
# (Regra da Madrugada) e desenha uma planilha `.xlsx` com formatação e 
# cores automáticas prontas para envio à diretoria.
# ==============================================================================

import pandas as pd     # Para manipulação dos blocos de dados.
import sqlite3          # Para leitura segura do banco de dados local.
import os               # Interação com pastas e caminhos.
import sys              # Para modularização e navegação no Python.

# Bibliotecas do OpenPyXL responsáveis por desenhar e pintar a planilha (Estilização Automática)
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# ==============================================================================
# 1. MODULARIZAÇÃO E CONEXÃO
# ==============================================================================
# Sobe um nível no sistema de pastas ('..') para encontrar o 'utils.py'.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents

def gerar_relatorio_final():
    # ==========================================================================
    # 2. LOCALIZAÇÃO E LEITURA DO BANCO DE DADOS
    # ==========================================================================
    caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')
    
    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: O banco de dados não foi encontrado em: {caminho_db}")
        return

    try:
        conn = sqlite3.connect(caminho_db)
        
        # A Query Mestra de BI: Une Pacientes com seus Atendimentos sem criar Clones.
        query = """
        SELECT DISTINCT p.nome, p.dn, p.idade, p.sexo, p.raca, p.cidade, 
        a.data_atendimento, a.hora_atendimento, p.cpf, p.sus, p.endereco, p.numero, p.bairro, p.tel, 
        a.procedencia
        FROM pacientes p
        JOIN atendimentos a ON (p.cpf = a.cpf AND p.cpf != '') OR (p.sus = a.sus AND p.sus != '')
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # 🛡️ O EXTERMINADOR DE CLONES: Trava de segurança suprema do Pandas.
        # Caso tenha ocorrido "Efeito Metralhadora" no teclado da recepção, 
        # ele apaga as linhas idênticas baseadas na tripla [Nome + Data + Hora].
        df = df.drop_duplicates(subset=['nome', 'data_atendimento', 'hora_atendimento'])
        
    except Exception as e:
        print(f"❌ Erro ao ler o banco: {e}")
        return

    # ==========================================================================
    # 3. INTELIGÊNCIA TEMPORAL ("A REGRA DA MADRUGADA")
    # ==========================================================================
    # Junta a data e a hora num objeto só para facilitar o cálculo do tempo.
    df['dt_entrada'] = pd.to_datetime(df['data_atendimento'] + ' ' + df['hora_atendimento'], errors='coerce')
    df = df.dropna(subset=['dt_entrada', 'nome'])   # Remove linhas que não tenham data ou nome.
    df = df[df['nome'].str.strip() != '']           # Remove nomes que sejam apenas um "espaço em branco".

    # A Função Lógica do Hospital (O pulo do gato):
    # Se o paciente chegou às 03:00 da manhã de quarta, essa função subtrai 1 dia do calendário 
    # para jogar ele na conta do plantão da noite de terça.
    df['Data_Logica'] = df['dt_entrada'].apply(
        lambda x: (x - pd.Timedelta(days=1)).date() if x.hour < 7 else x.date()
    )
    
    # Cria uma coluna apenas com o Mês e Ano (Ex: 04-2026) para facilitar o filtro da recepcionista.
    df['Mes_Ref'] = pd.to_datetime(df['Data_Logica']).dt.strftime('%m-%Y')

    # ==========================================================================
    # 4. INTERAÇÃO E FILTRAGEM DO MÊS
    # ==========================================================================
    meses = sorted(df['Mes_Ref'].unique())
    print(f"\n📅 Meses detectados no sistema: {meses}")
    escolha = input("👉 Digite o mês que deseja gerar (Ex: 04-2026): ").strip()
    
    df_mes = df[df['Mes_Ref'] == escolha].copy()
    if df_mes.empty:
        print(f"❌ Nenhum atendimento encontrado para {escolha}.")
        return

    # ==========================================================================
    # 5. ORGANIZAÇÃO EM LOTES (PANDAS GROUPBY + UTILS)
    # ==========================================================================
    colunas = ['Nº', 'Nome do Paciente', 'Data Nasc.', 'Idade', 'Sexo', 'Raça/Cor',
               'Município', 'Hora', 'CPF', 'Cartão SUS', 'Procedência', 'Endereço', 'Telefone']
    dados_finais = []
    
    df_mes = df_mes.sort_values('dt_entrada') # Ordena cronologicamente do dia 1 ao 30
    
    # O .groupby separa a planilha mãe em mini-planilhas baseadas em Data Lógica e Turno de trabalho.
    grupos = df_mes.groupby([
        'Data_Logica', 
        df_mes['dt_entrada'].dt.hour.apply(lambda x: 'DIURNO' if 7<=x<19 else 'NOTURNO')
    ], sort=False)

    print(f"🧹 Formatando dados de {escolha} para o padrão Excel...")

    # Loop para processar os grupos um a um
    for (data, turno), grupo in grupos:
        # Cria uma linha especial (Cabeçalho de Plantão) com texto mesclado
        dados_finais.append({'Nº': f"PLANTÃO {turno} - {data.strftime('%d/%m/%Y')}"})
        
        # O enumerate(..., 1) conta a posição para criar os numerais de chamada (1, 2, 3...)
        for i, (_, r) in enumerate(grupo.iterrows(), 1):
            
            # Higienização Final antes do Excel via utils.py
            nome_limpo = remove_accents(r['nome'])
            cidade_limpa = remove_accents(r['cidade'])
            bairro_limpo = remove_accents(r['bairro'])
            rua_limpa = remove_accents(r['endereco'])
            
            # Limpa documentos para evitar que o Excel ache que são fórmulas e exiba '####'
            cpf_f = apenas_numeros(r['cpf'])
            sus_f = apenas_numeros(r['sus'])
            
            # Procedência
            proc = remove_accents(str(r['procedencia'])) if r['procedencia'] else ''
            if proc == 'NORMAL': proc = ''
            
            dn_br = pd.to_datetime(r['dn']).strftime('%d/%m/%Y') if r['dn'] and str(r['dn']) != 'nan' else ""
            end_f = f"{rua_limpa}, {str(r['numero'] or '').strip()} - {bairro_limpo}"

            # Monta o registro empacotando numa lista alinhada ao cabeçalho
            dados_finais.append({
                'Nº': i, 'Nome do Paciente': nome_limpo, 'Data Nasc.': dn_br,
                'Idade': r['idade'], 'Sexo': r['sexo'], 'Raça/Cor': r['raca'],
                'Município': cidade_limpa, 'Hora': r['dt_entrada'].strftime('%H:%M'),
                'CPF': cpf_f, 'Cartão SUS': sus_f, 'Procedência': proc, 
                'Endereço': end_f, 'Telefone': r['tel']
            })

    # ==========================================================================
    # 6. ENGENHARIA DE PLANILHA (OPENPYXL)
    # ==========================================================================
    nome_arq = "Relatorio_Producao_HMPCF.xlsx"
    
    # Se o arquivo já existe, nós carregamos ele e sobrescrevemos a aba do mês atual.
    # Isso impede a criação de infinitos arquivos na pasta.
    if os.path.exists(nome_arq):
        wb = load_workbook(nome_arq)
        if escolha in wb.sheetnames: 
            del wb[escolha]
        ws = wb.create_sheet(title=escolha)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = escolha

    # Insere o cabeçalho técnico na linha 1
    ws.append(colunas)

    # Descarrega os milhares de atendimentos na planilha física
    for linha in dados_finais:
        ws.append(list(linha.values()))

    # ==========================================================================
    # 7. ESTILIZAÇÃO (PINTURA DO EXCEL)
    # ==========================================================================
    # Definição dos perfis de estilo
    fill_not = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid") # Vermelho (Noite)
    fill_diu = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid") # Azul (Dia)
    font_h = Font(color="FFFFFF", bold=True) # Fonte Branca em Negrito
    center = Alignment(horizontal="center", vertical="center") # Alinhamento perfeito
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                    top=Side(style='thin'), bottom=Side(style='thin'))

    # Loop pela planilha inteira para pintar as linhas
    for row in range(1, ws.max_row + 1):
        primeira_celula = str(ws.cell(row=row, column=1).value)
        
        # Identifica se a linha atual é um "separador de plantão"
        if "PLANTÃO" in primeira_celula:
            # Mescla da coluna 1 até a 13 para formar o cabeçalho horizontal grande
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=13)
            
            # Dinâmica de Cores: Azul ou Vermelho?
            cor = fill_not if "NOTURNO" in primeira_celula else fill_diu
            
            for col in range(1, 14):
                c = ws.cell(row=row, column=col)
                c.fill, c.font, c.alignment = cor, font_h, center
        else:
            # Linha normal de paciente (Cria bordinhas)
            for col in range(1, 14):
                c = ws.cell(row=row, column=col)
                c.border = border
                # Centraliza textos menores como Idade(Col 5), Hora(Col 8), etc.
                if col in [6-8]: c.alignment = center

    # Configuração da largura das colunas do Excel para não cortar o nome de ninguém
    dims = {'A':6, 'B':35, 'C':12, 'D':6, 'E':6, 'F':12, 'G':15, 'H':8, 
            'I':15, 'J':18, 'K':15, 'L':40, 'M':15}
    for col, width in dims.items():
        ws.column_dimensions[col].width = width

    # Trava o painel na célula A2 para que o cabeçalho acompanhe a rolagem
    ws.freeze_panes = 'A2'
    
    # Salva fisicamente o disco
    wb.save(nome_arq)
    print(f"✅ Relatório '{escolha}' gerado com sucesso em '{nome_arq}'!")

if __name__ == "__main__":
    gerar_relatorio_final()