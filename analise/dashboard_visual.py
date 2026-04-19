# ==============================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO VISUAL E BI (DASHBOARD)
# ==============================================================================
# OBJETIVO:
# Este script atua como o "Cientista de Dados" do hospital. Ele se conecta ao
# banco de dados (SQLite), extrai os atendimentos do mês, higieniza os dados 
# e gera um painel gráfico profissional (Dashboard) em alta resolução (.png).
# ==============================================================================

import os               # Interação com o Sistema Operacional (caminhos de arquivos).
import sqlite3          # Biblioteca nativa para executar comandos SQL no banco de dados.
import pandas as pd     # A biblioteca mais poderosa do Python para Análise de Dados (Criação de Tabelas/DataFrames).
import matplotlib.pyplot as plt # O motor base de renderização para desenhar gráficos.
import seaborn as sns   # Uma camada extra sobre o matplotlib que deixa os gráficos muito mais bonitos e profissionais.
import sys              # Módulo de sistema, usado aqui para manipular os caminhos de importação do Python.

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E MODULARIZAÇÃO
# ==============================================================================
# O comando abaixo adiciona a pasta "pai" (um nível acima) ao escopo do Python.
# Isso permite que este script, que está dentro da pasta 'analise', consiga 
# achar e importar a ferramenta 'utils.py' que está na pasta principal.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import remove_accents # Importa nossa função de limpeza de texto.

def gerar_super_relatorio_mensal():
    # ==========================================================================
    # 2. INTERAÇÃO E ENTRADA DE DADOS (USER INPUT)
    # ==========================================================================
    print("\n📅 CONFIGURAÇÃO DO RELATÓRIO MENSAL E GRÁFICOS")
    mes_ano = input("Qual mês/ano deseja analisar? (Formato MM/AAAA, ex: 04/2026): ").strip()
    
    try:
        # O método .split('/') divide a string onde tem a barra. Ex: '04/2026' vira ['04', '2026']
        mes_filtro, ano_filtro = mes_ano.split('/')
    except ValueError:
        # Prevenção de Erros: Se o usuário digitar 'abril', o split falha e o sistema avisa amigavelmente.
        print("❌ Formato inválido! Use MM/AAAA")
        return

    # ==========================================================================
    # 3. CONEXÃO COM O BANCO DE DADOS (ROTEAMENTO INTELIGENTE)
    # ==========================================================================
    # '..' significa "volte uma pasta". Assim garantimos que o código ache o banco independente do PC.
    caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')
    
    if not os.path.exists(caminho_db):
        print(f"❌ Erro: hospital.db não encontrado em {caminho_db}")
        return
        
    conn = sqlite3.connect(caminho_db)

    # ==========================================================================
    # 4. INTELIGÊNCIA DE NEGÓCIO: TOP 30 PACIENTES RECORRENTES (SQL AVANÇADO)
    # ==========================================================================
    # Usamos uma CTE (Common Table Expression) chamada 'AtendimentosLimpos' iniciada com 'WITH'.
    # O DISTINCT na query evita o "Efeito Cartesiano", impedindo duplicações.
    query_texto = f"""
    WITH AtendimentosLimpos AS (
        SELECT DISTINCT p.nome, p.cpf, p.sus, a.data_atendimento, a.hora_atendimento
        FROM atendimentos a
        JOIN pacientes p ON (a.cpf = p.cpf AND p.cpf != '') OR (a.sus = p.sus AND p.sus != '')
        WHERE a.data_atendimento LIKE '{ano_filtro}-{mes_filtro}-%'
    )
    SELECT nome, COUNT(*) as total, GROUP_CONCAT(hora_atendimento, ' | ') as horas
    FROM AtendimentosLimpos
    GROUP BY nome, cpf, sus
    HAVING total > 1
    ORDER BY total DESC
    LIMIT 30
    """
    
    try:
        # O Pandas executa a query SQL e transforma a resposta num DataFrame (planilha em memória)
        df_texto = pd.read_sql_query(query_texto, conn)
        print("\n📋 TOP 30 PACIENTES RECORRENTES (Dados Padronizados):")
        
        if df_texto.empty:
            print(f"   ⚠ Nenhum retorno múltiplo em {mes_filtro}/{ano_filtro}.")
        else:
            # .iterrows() faz um loop passando linha por linha do DataFrame
            for _, linha in df_texto.iterrows():
                # Formatação de string avançada: [:30] corta o nome para caber na tela
                # e :<30 alinha o texto à esquerda (padding).
                nome_formatado = remove_accents(linha['nome'])[:30]
                print(f"   👤 {nome_formatado:<30} | Retornos: {linha['total']} | Horas: {linha['horas']}")
    except Exception as e:
        print(f"   ❌ Erro na consulta: {e}")

    # ==========================================================================
    # 5. EXTRAÇÃO DE DADOS PARA OS GRÁFICOS
    # ==========================================================================
    query_graficos = f"""
    SELECT DISTINCT p.cpf, p.sus, a.data_atendimento, a.hora_atendimento, p.idade, p.sexo, p.bairro
    FROM atendimentos a
    JOIN pacientes p ON (a.cpf = p.cpf AND p.cpf != '') OR (a.sus = p.sus AND p.sus != '')
    WHERE a.data_atendimento LIKE '{ano_filtro}-{mes_filtro}-%'
    """
    df_mensal = pd.read_sql_query(query_graficos, conn)
    conn.close() # Fechamos o banco aqui, pois o Pandas já guardou os dados na memória RAM (df_mensal).

    if df_mensal.empty:
        print(f"\n🛑 Sem dados para gerar gráficos em {mes_ano}.")
        return

    # ==========================================================================
    # 6. LIMPEZA PROFUNDA COM PANDAS E LAMBDA FUNÇÕES
    # ==========================================================================
    # Função Lambda: Uma função "anônima" aplicada a todas as linhas ao mesmo tempo.
    # Higieniza bairros (ex: junta "Centro" e "CENTRO" e tira acentos) para não gerar colunas duplicadas no gráfico.
    df_mensal['bairro'] = df_mensal['bairro'].apply(lambda x: remove_accents(str(x)).strip())
    
    # errors='coerce' transforma letras ou erros em 'NaN' (Not a Number), impedindo o sistema de travar.
    df_mensal['idade'] = pd.to_numeric(df_mensal['idade'], errors='coerce')
    
    # Filtro de Sanidade: Só aceita idades entre 0 e 120 anos.
    df_idade_limpa = df_mensal[(df_mensal['idade'] >= 0) & (df_mensal['idade'] <= 120)].copy()

    # ==========================================================================
    # 7. RENDERIZAÇÃO DO DASHBOARD (MATPLOTLIB + SEABORN)
    # ==========================================================================
    print(f"\n🎨 Renderizando dashboard_{mes_filtro}_{ano_filtro}.png...")
    sns.set_theme(style="whitegrid") # Coloca as linhas de fundo para facilitar a leitura visual
    
    # Cria uma "tela" (fig) dividida em 4 quadrantes (2x2) chamada axes.
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # --- [Gráfico 1: Perfil Etário (Histograma Empilhado)] ---
    df_is = df_idade_limpa[df_idade_limpa['sexo'].isin(['M', 'F'])]
    if not df_is.empty:
        sns.histplot(data=df_is, x='idade', hue='sexo', multiple='stack', 
                     palette={'M': '#3498db', 'F': '#e74c3c'}, kde=True, ax=axes)
        axes.set_title(f'Perfil Etário por Sexo ({mes_ano})', fontweight='bold')

    # --- [Gráfico 2: Top Bairros (Barras Horizontais)] ---
    # value_counts() conta quantas vezes cada bairro aparece e .head(10) pega apenas os 10 maiores.
    top_bairros = df_mensal[df_mensal['bairro'] != '']['bairro'].value_counts().head(10)
    if not top_bairros.empty:
        sns.barplot(x=top_bairros.values, y=top_bairros.index, hue=top_bairros.index, 
                    legend=False, palette='viridis', ax=axes[1])
        axes[1].set_title('Top 10 Bairros (Dados Sanitizados)', fontweight='bold')

    # --- [Gráfico 3: Picos de Horário na Recepção] ---
    # Quebra o horário (Ex: '14:30' -> Pega só o '14') para ver em qual hora do dia a recepção lota mais.
    df_mensal['h'] = pd.to_numeric(df_mensal['hora_atendimento'].str.split(':').str, errors='coerce')
    sns.countplot(data=df_mensal, x='h', color='coral', ax=axes[1])
    axes[1].set_title('Picos de Horário na Recepção', fontweight='bold')

    # --- [Gráfico 4: Volume Diário (Linha do Tempo)] ---
    df_mensal['dia'] = df_mensal['data_atendimento'].str.split('-').str[-1]
    dias_ordenados = sorted(df_mensal['dia'].dropna().unique())
    sns.countplot(data=df_mensal, x='dia', palette='Blues_d', hue='dia', legend=False, ax=axes[1], order=dias_ordenados)
    axes[1].set_title('Volume de Atendimentos por Dia', fontweight='bold')

    # tight_layout() organiza os gráficos para os títulos não ficarem sobrepostos.
    plt.tight_layout()
    
    # Exportação final em alta resolução (300 DPI é padrão de impressão fotográfica).
    nome_saida = f"dashboard_{mes_filtro}_{ano_filtro}.png"
    plt.savefig(nome_saida, dpi=300)
    print(f"✅ Dashboard salvo com sucesso!")

# Executa a função principal caso este arquivo não esteja sendo importado por outro.
if __name__ == "__main__":
    gerar_super_relatorio_mensal()
