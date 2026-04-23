# ==============================================================================
# 📊 SISTEMA DE BI: DASHBOARD VISUAL E RELATÓRIO EXECUTIVO (HMPCF)
# ==============================================================================
# OBJETIVO:
# 1. Conectar ao banco de dados e higienizar os registros.
# 2. Gerar um relatório textual detalhado dos 20 pacientes com mais retornos.
# 3. Renderizar um Dashboard visual em PNG corrigindo conflitos de eixos (Axes).
# ==============================================================================

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E BLINDAGEM DE ROTAS
# ==============================================================================
pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))

if pasta_atual not in sys.path: sys.path.append(pasta_atual)
if pasta_pai not in sys.path: sys.path.append(pasta_pai)

# ==============================================================================
# 2. MÓDULO DE AUDITORIA: RELATÓRIO TOP 20
# ==============================================================================
def relatorio_top_20_detalhado(df):
    """
    Identifica os 20 pacientes com maior volume de entradas no mês,
    exibindo a linha do tempo exata de cada visita e o Cartão SUS.
    """
    print("\n" + "="*60)
    print("🏆 TOP 20 PACIENTES COM MAIS ENTRADAS NO MÊS")
    print("="*60 + "\n")
    
    # Filtra apenas registros que possuam um SUS preenchido para evitar agrupar "vazios"
    df_valido = df[df['sus'].astype(str).str.strip() != '']
    df_valido = df_valido[df_valido['sus'].notna()]
    
    # Conta a frequência de cada SUS e pega os 20 primeiros
    top_20_sus = df_valido['sus'].value_counts().head(20).index
    
    # Filtra o DataFrame geral para conter APENAS esses 20 pacientes
    df_top20 = df_valido[df_valido['sus'].isin(top_20_sus)].copy()
    
    # Ordena cronologicamente para a linha do tempo fazer sentido no terminal
    df_top20 = df_top20.sort_values(by=['nome', 'data_atendimento', 'hora_atendimento'])
    
    posicao = 1
    for sus in top_20_sus:
        # Isola os dados de um único paciente por vez
        dados_paciente = df_top20[df_top20['sus'] == sus]
        if dados_paciente.empty: continue
        
        nome = dados_paciente['nome'].iloc[0]
        total_entradas = len(dados_paciente)
        
        print(f"[{posicao}º] 👤 {nome}")
        print(f"      🏥 SUS: {sus} | 🔄 Total: {total_entradas} entradas")
        print("      " + "-" * 40)
        
        # Imprime cada data e hora em que ele passou pela recepção
        for idx, row in dados_paciente.iterrows():
            data = row['data_atendimento']
            hora = row['hora_atendimento']
            print(f"        ➜ Data: {data} às {hora}")
            
        print("\n")
        posicao += 1

# ==============================================================================
# 3. MÓDULO VISUAL: GERAÇÃO DO DASHBOARD (PNG)
# ==============================================================================
def gerar_super_relatorio_mensal():
    print("⏳ Conectando ao banco de dados e extraindo informações...")
    
    # Conecta ao banco na pasta pai
    caminho_db = os.path.join(pasta_pai, 'hospital.db')
    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: Banco de dados não encontrado em {caminho_db}")
        return

    conn = sqlite3.connect(caminho_db)

    # O JOIN mescla as informações pessoais do paciente com o histórico de visitas dele
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
        print("🛑 Não há dados suficientes no banco para gerar o Dashboard.")
        return

    # 1º PASSO: Gera o relatório no terminal para a sua auditoria
    relatorio_top_20_detalhado(df_mensal)

    print("🎨 Renderizando dashboard_04_2026.png...")

    # Configuração visual base do Seaborn
    sns.set_theme(style="whitegrid")
    
    # 🎯 CORREÇÃO DO ERRO 'numpy.ndarray': 
    # Criamos uma tela com 4 espaços (2 linhas, 2 colunas). 
    # A variável 'axes' agora é uma matriz, então precisamos dizer exatamente 
    # em qual quadrante o gráfico vai (Ex: axes[0, 0] é o topo-esquerdo).
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Visão Geral de Atendimentos - HMPCF', fontsize=20, fontweight='bold')

    # --- [GRÁFICO 1: Histograma de Idade por Sexo] (Topo-Esquerdo) ---
    # Limpa a coluna de idade (tira a palavra "Anos" se houver) para o gráfico conseguir somar
    df_mensal['idade_num'] = pd.to_numeric(df_mensal['idade'].str.replace(' Anos', '', regex=False), errors='coerce')
    
    sns.histplot(data=df_mensal, x='idade_num', hue='sexo', multiple='stack',
                 palette={'M': '#3498db', 'F': '#e74c3c', 'MASCULINO': '#3498db', 'FEMININO': '#e74c3c'}, 
                 kde=True, ax=axes[0, 0])
    axes[0, 0].set_title('Distribuição de Idade por Sexo', fontweight='bold')
    axes[0, 0].set_xlabel('Idade')
    axes[0, 0].set_ylabel('Quantidade de Pacientes')

    # --- [GRÁFICO 2: Top 10 Bairros] (Topo-Direito) ---
    # Verifica se a coluna bairro existe e tem dados, senão ignora o gráfico para não quebrar
    if 'bairro' in df_mensal.columns and not df_mensal['bairro'].isna().all():
        top_bairros = df_mensal['bairro'].value_counts().head(10)
        sns.barplot(x=top_bairros.values, y=top_bairros.index,
                    palette='viridis', ax=axes[0, 1], hue=top_bairros.index, legend=False)
        axes[0, 1].set_title('Top 10 Bairros (Procedência)', fontweight='bold')
        axes[0, 1].set_xlabel('Número de Atendimentos')
    else:
        axes[0, 1].set_title('Dados de Bairro Indisponíveis', fontweight='bold')

    # --- [GRÁFICO 3: Picos de Horário na Recepção] (Base-Esquerda) ---
    # Quebra a string "14:30" e pega apenas o "14" para criar o pico de calor por hora
    df_mensal['h'] = pd.to_numeric(df_mensal['hora_atendimento'].str.split(':').str[0], errors='coerce')
    sns.countplot(data=df_mensal, x='h', color='coral', ax=axes[1, 0])
    axes[1, 0].set_title('Picos de Horário na Recepção', fontweight='bold')
    axes[1, 0].set_xlabel('Hora do Dia (0h - 23h)')
    axes[1, 0].set_ylabel('Volume de Entradas')

    # --- [GRÁFICO 4: Volume Diário] (Base-Direita) ---
    # Inteligência para extrair apenas o DIA, não importa se a data está 15/04/2026 ou 2026-04-15
    df_mensal['dia'] = df_mensal['data_atendimento'].apply(
        lambda x: str(x).split('/')[-3] if '/' in str(x) else str(x).split('-')[-1]
    )
    dias_ordenados = sorted(df_mensal['dia'].dropna().unique())
    
    sns.countplot(data=df_mensal, x='dia', palette='Blues_d', hue='dia', legend=False, ax=axes[1, 1], order=dias_ordenados)
    axes[1, 1].set_title('Volume de Atendimentos por Dia', fontweight='bold')
    axes[1, 1].set_xlabel('Dia do Mês')
    axes[1, 1].set_ylabel('Total de Atendimentos')

    # Ajusta os espaçamentos automáticos para os títulos não encavalarem nos gráficos
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    # Salva a imagem final em alta resolução
    nome_arquivo = 'dashboard_04_2026.png'
    plt.savefig(nome_arquivo, dpi=300)
    print(f"✅ Dashboard gerado com sucesso! Arquivo salvo como: {nome_arquivo}")

# ==============================================================================
# INICIALIZADOR
# ==============================================================================
if __name__ == "__main__":
    gerar_super_relatorio_mensal()