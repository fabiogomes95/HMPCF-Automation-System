# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO VISUAL (DASHBOARD)
# Desenvolvido para analisar o banco SQLite e gerar gráficos analíticos.
# Com Filtro Anti-Clones e Análise de Recorrência (Top 30)
# =========================================================================

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def gerar_super_relatorio_mensal():
    # ---------------------------------------------------------------------
    # ETAPA 1: ENTRADA DO USUÁRIO
    # ---------------------------------------------------------------------
    print("\n📅 CONFIGURAÇÃO DO RELATÓRIO MENSAL E GRÁFICOS")
    mes_ano = input("Qual mês/ano deseja analisar? (Formato MM/AAAA, ex: 03/2026): ").strip()
    
    try:
        mes_filtro, ano_filtro = mes_ano.split('/')
    except ValueError:
        print("❌ Formato inválido! Use MM/AAAA (exemplo: 03/2026)")
        return

    print("\n" + "="*70)
    print(f"📊 PROCESSANDO PAINEL DE DADOS: {mes_filtro}/{ano_filtro}")
    print("="*70)

    # ---------------------------------------------------------------------
    # ETAPA 2: LOCALIZAR O BANCO DE DADOS (GPS Inteligente)
    # ---------------------------------------------------------------------
    caminho_db = '../hospital.db' 
    
    if not os.path.exists(caminho_db):
        caminho_db = 'hospital.db' 
        if not os.path.exists(caminho_db):
            print("❌ Erro: Arquivo hospital.db não encontrado!")
            return
            
    conn = sqlite3.connect(caminho_db)

    # ---------------------------------------------------------------------
    # ETAPA 3: RELATÓRIO TEXTUAL (Top 30 Pacientes Recorrentes)
    # ---------------------------------------------------------------------
    # O comando WITH cria uma "Tabela Virtual Temporária" limpa antes de contar.
    # O DISTINCT apaga os horários clonados (ex: cliques duplos no botão Salvar).
    # O HAVING total > 1 esconde quem foi apenas 1 vez ao hospital.
    # O LIMIT 30 restringe a impressão aos 30 pacientes que mais voltaram.
    query_texto = f"""
        WITH AtendimentosLimpos AS (
            SELECT DISTINCT 
                p.nome, p.cpf, p.sus, a.data_atendimento, a.hora_atendimento
            FROM atendimentos a
            JOIN pacientes p ON (a.cpf = p.cpf AND p.cpf != '') OR (a.sus = p.sus AND p.sus != '')
            WHERE a.data_atendimento LIKE '{ano_filtro}-{mes_filtro}-%'
        )
        SELECT 
            nome, 
            COUNT(*) as total,
            GROUP_CONCAT(hora_atendimento, ' | ') as horas
        FROM AtendimentosLimpos
        GROUP BY nome, cpf, sus
        HAVING total > 1
        ORDER BY total DESC
        LIMIT 30
    """
    
    try:
        df_texto = pd.read_sql_query(query_texto, conn)
        print("\n📋 TOP 30 PACIENTES RECORRENTES (Mais de 1 visita filtrada):")
        
        if df_texto.empty:
            print(f"   ⚠ Nenhum paciente retornou mais de 1 vez em {mes_filtro}/{ano_filtro}.")
        else:
            for _, linha in df_texto.iterrows():
                nome_formatado = linha['nome'][:30] # Limita a 30 letras 
                # O print agora mostra apenas as pessoas reais, com horários reais e sem poluição!
                print(f"   👤 {nome_formatado:<30} | Retornos reais: {linha['total']} | Horas: {linha['horas']}")
    except Exception as e:
        print(f"   ❌ Erro na consulta de texto: {e}")

    # ---------------------------------------------------------------------
    # ETAPA 4: EXTRAIR DADOS PARA OS GRÁFICOS (Sem barras distorcidas)
    # ---------------------------------------------------------------------
    # O SELECT DISTINCT garante que se a recepcionista clicou 5 vezes sem 
    # querer no botão Salvar, o gráfico contabilize o paciente apenas UMA vez!
    query_graficos = f"""
        SELECT DISTINCT 
            p.cpf, p.sus, a.data_atendimento, a.hora_atendimento, 
            p.idade, p.sexo, p.bairro, p.tel
        FROM atendimentos a
        JOIN pacientes p ON (a.cpf = p.cpf AND p.cpf != '') OR (a.sus = p.sus AND p.sus != '')
        WHERE a.data_atendimento LIKE '{ano_filtro}-{mes_filtro}-%'
    """
    
    df_mensal = pd.read_sql_query(query_graficos, conn)
    conn.close() # Fecha a conexão com o banco

    if df_mensal.empty:
        print(f"\n🛑 Sem dados suficientes para gerar os gráficos de {mes_ano}.")
        return

    # ---------------------------------------------------------------------
    # ETAPA 5: TRATAMENTO E LIMPEZA DE DADOS (Data Cleaning)
    # ---------------------------------------------------------------------
    # Força a coluna 'idade' a ser tratada como número matemático
    df_mensal['idade'] = pd.to_numeric(df_mensal['idade'], errors='coerce')
    
    # Filtra apenas idades que fazem sentido (entre 0 e 120 anos)
    df_idade_limpa = df_mensal[(df_mensal['idade'] >= 0) & (df_mensal['idade'] <= 120)].copy()

   # ---------------------------------------------------------------------
    # ETAPA 6: DESENHAR OS GRÁFICOS (Seaborn)
    # ---------------------------------------------------------------------
    print(f"\n🎨 Renderizando gráficos perfeitamente limpos...")
    sns.set_theme(style="whitegrid") 
    
    # Cria uma folha de imagem (16x12 polegadas) com 4 espaços (2x2)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # --- [Gráfico 1: Cima Esquerda -> Coordenada 0, 0] ---
    df_is = df_idade_limpa[df_idade_limpa['sexo'].isin(['M', 'F'])]
    if not df_is.empty:
        sns.histplot(data=df_is, x='idade', hue='sexo', multiple='stack', 
                     palette={'M': '#3498db', 'F': '#e74c3c'}, kde=True, ax=axes[0, 0]) # Ajustado: [0, 0]
    axes[0, 0].set_title(f'Perfil Etário e Sexo ({mes_ano})', fontweight='bold')
    axes[0, 0].set_ylabel('Quantidade de Visitas Reais')

    # --- [Gráfico 2: Cima Direita -> Coordenada 0, 1] ---
    top_bairros = df_mensal[df_mensal['bairro'] != '']['bairro'].value_counts().head(10)
    if not top_bairros.empty:
        sns.barplot(x=top_bairros.values, y=top_bairros.index, hue=top_bairros.index, 
                    legend=False, palette='viridis', ax=axes[0, 1]) # Ajustado: [0, 1]
    axes[0, 1].set_title('Top 10 Bairros Atendidos no Mês', fontweight='bold')
    axes[0, 1].set_xlabel('Quantidade')

    # --- [Gráfico 3: Baixo Esquerda -> Coordenada 1, 0] ---
    # Nota: Verifique se o split está correto para extrair a hora
    df_mensal['h'] = pd.to_numeric(df_mensal['hora_atendimento'].str.split(':').str[0], errors='coerce')
    sns.countplot(data=df_mensal, x='h', color='coral', ax=axes[1, 0]) # Ajustado: [1, 0]
    axes[1, 0].set_title('Picos de Horário na Recepção', fontweight='bold')
    axes[1, 0].set_xlabel('Hora do Dia (0h - 23h)')
    axes[1, 0].set_ylabel('Volume')

   # --- [Gráfico 4: Baixo Direita -> Coordenada 1, 1] ---
    df_mensal['dia'] = df_mensal['data_atendimento'].str.split('-').str[-1] 
    
    # Pega os dias únicos encontrados no mês e organiza do menor para o maior
    dias_ordenados = sorted(df_mensal['dia'].dropna().unique())
    
    # Adicionamos o comando 'order=dias_ordenados' para forçar o gráfico a seguir a linha do tempo!
    sns.countplot(data=df_mensal, x='dia', palette='Blues_d', hue='dia', legend=False, ax=axes[1, 1], order=dias_ordenados) 
    
    axes[1, 1].set_title('Volume de Atendimentos por Dia', fontweight='bold')
    axes[1, 1].set_xlabel('Dia do Mês')
    axes[1, 1].set_ylabel('Volume')
    # Organiza os gráficos para nenhum texto se sobrepor
    plt.tight_layout()
    # ---------------------------------------------------------------------
    # ETAPA 7: EXPORTAR A IMAGEM
    # ---------------------------------------------------------------------
    nome_saida = f"dashboard_{mes_filtro}_{ano_filtro}.png"
    plt.savefig(nome_saida, dpi=300) # Salva a foto em 4K
    
    print(f"✅ Dashboard visual salvo como: '{nome_saida}'")
    print("="*70 + "\n")

# Ponto de Partida do Script
if __name__ == "__main__":
    gerar_super_relatorio_mensal()