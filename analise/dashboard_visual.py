# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO VISUAL (DASHBOARD)
# Desenvolvido para analisar o banco SQLite e gerar gráficos analíticos.
# Versão Integrada com utils.py para limpeza de dados profissional.
# =========================================================================

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys

# --- CONEXÃO COM A RAIZ (Para achar o utils.py) ---
# Como este script está em 'analise_dados/', subimos um nível (..)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import remove_accents

def gerar_super_relatorio_mensal():
    # ---------------------------------------------------------------------
    # ETAPA 1: ENTRADA E FILTRO
    # ---------------------------------------------------------------------
    print("\n📅 CONFIGURAÇÃO DO RELATÓRIO MENSAL E GRÁFICOS")
    mes_ano = input("Qual mês/ano deseja analisar? (Formato MM/AAAA, ex: 04/2026): ").strip()
    
    try:
        mes_filtro, ano_filtro = mes_ano.split('/')
    except ValueError:
        print("❌ Formato inválido! Use MM/AAAA")
        return

    # ---------------------------------------------------------------------
    # ETAPA 2: LOCALIZAR O BANCO DE DADOS
    # ---------------------------------------------------------------------
    caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')
    
    if not os.path.exists(caminho_db):
        print(f"❌ Erro: hospital.db não encontrado em {caminho_db}")
        return
            
    conn = sqlite3.connect(caminho_db)

    # ---------------------------------------------------------------------
    # ETAPA 3: RELATÓRIO TEXTUAL (Top 30 Pacientes Recorrentes)
    # ---------------------------------------------------------------------
    query_texto = f"""
        WITH AtendimentosLimpos AS (
            SELECT DISTINCT 
                p.nome, p.cpf, p.sus, a.data_atendimento, a.hora_atendimento
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
        df_texto = pd.read_sql_query(query_texto, conn)
        print("\n📋 TOP 30 PACIENTES RECORRENTES (Dados Padronizados):")
        
        if df_texto.empty:
            print(f"   ⚠ Nenhum retorno múltiplo em {mes_filtro}/{ano_filtro}.")
        else:
            for _, linha in df_texto.iterrows():
                # Aplicamos o remove_accents para garantir a estética do relatório
                nome_formatado = remove_accents(linha['nome'])[:30]
                print(f"   👤 {nome_formatado:<30} | Retornos: {linha['total']} | Horas: {linha['horas']}")
    except Exception as e:
        print(f"   ❌ Erro na consulta: {e}")

    # ---------------------------------------------------------------------
    # ETAPA 4: EXTRAIR E LIMPAR DADOS PARA OS GRÁFICOS
    # ---------------------------------------------------------------------
    query_graficos = f"""
        SELECT DISTINCT 
            p.cpf, p.sus, a.data_atendimento, a.hora_atendimento, 
            p.idade, p.sexo, p.bairro
        FROM atendimentos a
        JOIN pacientes p ON (a.cpf = p.cpf AND p.cpf != '') OR (a.sus = p.sus AND p.sus != '')
        WHERE a.data_atendimento LIKE '{ano_filtro}-{mes_filtro}-%'
    """
    
    df_mensal = pd.read_sql_query(query_graficos, conn)
    conn.close()

    if df_mensal.empty:
        print(f"\n🛑 Sem dados para gerar gráficos em {mes_ano}.")
        return

    # --- LIMPEZA COM PANDAS + UTILS (O toque de mestre) ---
    # Limpamos os bairros para que "Centro" e "CENTRO" virem uma categoria só no gráfico
    df_mensal['bairro'] = df_mensal['bairro'].apply(lambda x: remove_accents(str(x)).strip())
    
    # Tratamento de idade
    df_mensal['idade'] = pd.to_numeric(df_mensal['idade'], errors='coerce')
    df_idade_limpa = df_mensal[(df_mensal['idade'] >= 0) & (df_mensal['idade'] <= 120)].copy()

    # ---------------------------------------------------------------------
    # ETAPA 5: DESENHAR O DASHBOARD (Seaborn)
    # ---------------------------------------------------------------------
    print(f"\n🎨 Renderizando dashboard_{mes_filtro}_{ano_filtro}.png...")
    sns.set_theme(style="whitegrid") 
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # [Gráfico 1: Perfil Etário]
    df_is = df_idade_limpa[df_idade_limpa['sexo'].isin(['M', 'F'])]
    if not df_is.empty:
        sns.histplot(data=df_is, x='idade', hue='sexo', multiple='stack', 
                     palette={'M': '#3498db', 'F': '#e74c3c'}, kde=True, ax=axes[0, 0])
    axes[0, 0].set_title(f'Perfil Etário por Sexo ({mes_ano})', fontweight='bold')

    # [Gráfico 2: Top Bairros (Agora agrupados corretamente!)]
    top_bairros = df_mensal[df_mensal['bairro'] != '']['bairro'].value_counts().head(10)
    if not top_bairros.empty:
        sns.barplot(x=top_bairros.values, y=top_bairros.index, hue=top_bairros.index, 
                    legend=False, palette='viridis', ax=axes[0, 1])
    axes[0, 1].set_title('Top 10 Bairros (Dados Sanitizados)', fontweight='bold')

    # [Gráfico 3: Picos de Horário]
    df_mensal['h'] = pd.to_numeric(df_mensal['hora_atendimento'].str.split(':').str[0], errors='coerce')
    sns.countplot(data=df_mensal, x='h', color='coral', ax=axes[1, 0])
    axes[1, 0].set_title('Picos de Horário na Recepção', fontweight='bold')

    # [Gráfico 4: Linha do Tempo (Dias do Mês)]
    df_mensal['dia'] = df_mensal['data_atendimento'].str.split('-').str[-1] 
    dias_ordenados = sorted(df_mensal['dia'].dropna().unique())
    sns.countplot(data=df_mensal, x='dia', palette='Blues_d', hue='dia', legend=False, ax=axes[1, 1], order=dias_ordenados) 
    axes[1, 1].set_title('Volume de Atendimentos por Dia', fontweight='bold')

    plt.tight_layout()
    
    # Exportação em Alta Definição
    nome_saida = f"dashboard_{mes_filtro}_{ano_filtro}.png"
    plt.savefig(nome_saida, dpi=300)
    print(f"✅ Dashboard salvo com sucesso!")

if __name__ == "__main__":
    gerar_super_relatorio_mensal()