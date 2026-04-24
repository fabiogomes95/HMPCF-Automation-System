# ==============================================================================
# 📄 MÓDULO DE RELATÓRIO E AUDITORIA (PDF) - HMPCF
# ==============================================================================
# DESENVOLVEDOR: Equipe de TI do Hospital Presidente Café Filho
# OBJETIVO PRINCIPAL:
#   Extrair os 20 pacientes com maior volume de entradas em um determinado 
#   período (Mensal, Trimestral ou Semestral), eliminar duplicatas geradas por 
#   erros de clique na recepção e exportar um PDF otimizado para impressão 
#   (Modo Econômico de Tinta) usando layout de duas colunas (Side-by-Side).
# ==============================================================================

# --- 1. IMPORTAÇÃO DAS FERRAMENTAS (BIBLIOTECAS) ---
import os           # Permite que o Python interaja com as pastas do Windows
import sqlite3      # O motor de banco de dados nativo do Python
import pandas as pd # Ferramenta avançada para tratar tabelas na memória (como um Excel invisível)
import sys          # Permite manipular as rotas do sistema operacional
from weasyprint import HTML # O "motor gráfico" que converte nosso código web em PDF
from datetime import datetime, timedelta # Ferramentas para fazer cálculos com datas e horas

# ==============================================================================
# 2. CONFIGURAÇÃO DE ROTAS (BLINDAGEM DE DIRETÓRIO)
# ==============================================================================
# Descobre exatamente em qual pasta este script (gerador_auditoria_pdf.py) está salvo.
pasta_atual = os.path.dirname(os.path.abspath(__file__))

# Como sabemos que o script está na pasta 'analise', mandamos o Python "subir um degrau" ('..')
# para encontrar o banco de dados que fica na pasta raiz (HMPCF-Automation-System).
pasta_raiz = os.path.abspath(os.path.join(pasta_atual, '..'))
caminho_db = os.path.join(pasta_raiz, 'hospital.db')


def calcular_data_inicio(meses):
    """
    Função matemática que descobre a data de corte retroativa.
    Ex: Se hoje é 24/04 e escolhemos 1 mês, ela calcula 30 dias para trás.
    """
    hoje = datetime.now() # Pega o relógio atual do computador
    
    # timedelta subtrai dias da data atual. Usamos meses * 30 como uma média confiável.
    data_calculada = hoje - timedelta(days=meses * 30)
    
    # Retorna a data no formato que o banco de dados entende (Ano-Mês-Dia)
    return data_calculada.strftime('%Y-%m-%d')


def gerar_auditoria_pdf():
    """Função principal que faz todo o trabalho pesado do relatório."""
    
    print("==================================================")
    print("📑 GERADOR DE RELATÓRIO DE AUDITORIA (PDF)")
    print("==================================================\n")

    # --- 3. MENU INTERATIVO PARA O USUÁRIO ---
    print("Escolha o período retroativo do relatório:")
    print("[1] Mensal (Últimos 30 dias)")
    print("[3] Trimestral (Últimos 90 dias)")
    print("[6] Semestral (Últimos 180 dias)")
    
    # O .strip() tira espaços sem querer que o usuário possa ter digitado
    opcao = input("\n👉 Digite a opção (1, 3 ou 6): ").strip()
    
    # Trava de segurança: Se digitar letra ou número errado, o programa para.
    if opcao not in ['1', '3', '6']:
        print("🛑 Opção inválida. Operação cancelada.")
        return
    
    # Converte o texto digitado em um número inteiro e calcula a data de corte
    qtd_meses = int(opcao)
    data_limite = calcular_data_inicio(qtd_meses)
    
    # Dicionário simples para dar um nome bonito ao arquivo final
    nomes_periodo = {'1': 'MENSAL', '3': 'TRIMESTRAL', '6': 'SEMESTRAL'}
    titulo_periodo = nomes_periodo[opcao]
    
    # Nome do arquivo PDF que será salvo na mesma pasta do script
    arquivo_pdf = os.path.join(pasta_atual, f"RELATORIO_AUDITORIA_{titulo_periodo}.pdf")

    # Verifica se o arquivo do banco realmente existe antes de tentar abrir
    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: Banco de dados não encontrado no caminho:\n{caminho_db}")
        return

    print(f"\n⏳ Conectando ao banco e buscando dados a partir de {data_limite}...")

    try:
        # --- 4. CONEXÃO E EXTRAÇÃO DE DADOS (A MÁGICA DO SQL) ---
        conn = sqlite3.connect(caminho_db)
        
        # O QUE ESTE SQL FAZ:
        # 1. SELECT DISTINCT: É a trava Anti-Duplicata. Se nome, cpf, sus, data e hora 
        #    forem rigorosamente iguais em duas linhas (duplo clique), ele puxa só uma!
        # 2. JOIN: Junta a ficha do paciente com as vezes que ele foi atendido.
        # 3. WHERE a.sus != '': Garante que não vamos puxar registros "fantasmas" sem documento.
        # 4. >= date(?): Filtra para puxar só do período que o usuário escolheu no menu.
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
        
        # O Pandas roda o SQL e já transforma o resultado numa super-tabela (DataFrame)
        df = pd.read_sql_query(query, conn, params=(data_limite,))
        conn.close() # Fechamos o banco assim que pegamos os dados para não travar o sistema

        # Se a tabela vier vazia, avisa o usuário e aborta
        if df.empty:
            print("🛑 Nenhum atendimento encontrado no período selecionado.")
            return

        # --- 5. PROCESSAMENTO DE DADOS (PANDAS) ---
        
        # Conta as ocorrências de cada número SUS e guarda os 20 que mais apareceram (Top 20)
        top_sus = df['sus'].value_counts().head(20).index
        
        # Cria uma nova tabela só com esses 20 pacientes, ordenando por nome, data e hora
        df_top20 = df[df['sus'].isin(top_sus)].sort_values(by=['nome', 'data_atendimento', 'hora_atendimento'])

        print("🏗️ Montando blocos de informação para o PDF...")

        # Variável vazia que vai guardar todo o código HTML gerado
        pacientes_html = ""

        # --- 6. GERAÇÃO DOS CARTÕES HTML (LAÇO DE REPETIÇÃO) ---
        for sus in top_sus:
            # Isola os dados de UM paciente por vez
            dados_p = df_top20[df_top20['sus'] == sus]
            if dados_p.empty: continue
            
            # Pega as informações cadastrais (pega da primeira linha, pois o nome não muda)
            nome = str(dados_p['nome'].iloc[0]).strip()
            cpf = str(dados_p['cpf'].iloc[0]).strip() if dados_p['cpf'].iloc[0] else "NÃO INFORMADO"
            total_entradas = len(dados_p) # Conta quantas linhas sobraram = total de visitas

            # Cria a lista do histórico (A Linha do Tempo)
            linhas_tempo = ""
            for i, (_, row) in enumerate(dados_p.iterrows(), start=1):
                d_br = row['data_atendimento']
                
                # Tenta formatar a data do padrão americano (YYYY-MM-DD) para brasileiro (DD/MM/YYYY)
                try:
                    if '-' in str(d_br):
                        d_br = datetime.strptime(d_br, '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    pass # Se der erro na formatação, deixa a data original para não travar o programa
                
                # Adiciona uma nova entrada na linha do tempo. Ex: [01] ➜ Data: 24/04/2026 às 14:30
                linhas_tempo += f"<div><span class='idx'>[{i:02d}]</span> ➜ Data: {d_br} às {row['hora_atendimento']}</div>"

            # Monta a "caixa visual" (Card) desse paciente no formato HTML
            pacientes_html += f"""
            <div class="patient-card">
                <div class="patient-name">👤 {nome}</div>
                <div class="patient-info">💳 <b>CPF:</b> {cpf}</div>
                <div class="patient-info">🏥 <b>SUS:</b> {sus}</div>
                <div class="patient-info">🔄 <b>TOTAL DE ENTRADAS:</b> {total_entradas} vez(es)</div>
                <div class="history-title">📅 LINHA DO TEMPO:</div>
                <div class="history-list">
                    {linhas_tempo}
                </div>
            </div>
            """

        # --- 7. A ESTRUTURA VISUAL DO DOCUMENTO (HTML + CSS) ---
        # Este é o "molde" da página do PDF, formatado no Modo Econômico (Ink-Saver).
        html_template = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                /* Configura a Folha A4, margens de 1.5cm e o rodapé automático de paginação */
                @page {{ 
                    size: A4; 
                    margin: 1.5cm; 
                    background-color: #ffffff; /* Fundo branco economiza tinta */
                    @bottom-right {{
                        content: "Página " counter(page) " de " counter(pages);
                        font-family: Arial, sans-serif;
                        font-size: 8pt;
                        color: #555;
                    }}
                }}
                
                /* Configurações gerais de texto e fundo da página inteira */
                body {{ font-family: 'Segoe UI', sans-serif; color: #000; background: #ffffff; margin: 0; }}
                
                /* Cabeçalho Limpo (Sem blocos pretos para poupar tonner) */
                .header {{ text-align: center; background-color: #ffffff; color: #000; padding: 10px 0; border-bottom: 2px solid #000; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 16pt; letter-spacing: 1px; font-weight: bold; }}
                .header p {{ margin: 5px 0 0 0; font-size: 10pt; color: #555; }}
                
                /* MÁGICA: column-count divide o espaço em duas colunas, reduzindo as páginas pela metade! */
                .container {{ column-count: 2; column-gap: 1.5cm; width: 100%; }}
                
                /* Estilo da caixa (Card) de cada paciente */
                .patient-card {{ 
                    break-inside: avoid; /* REGRA DE OURO: Impede que o paciente seja cortado no meio da página! */
                    page-break-inside: avoid;
                    background-color: #ffffff;
                    border: 1px solid #ccc; /* Borda bem fina e discreta */
                    border-left: 4px solid #333; /* Tarja escura na esquerda para destacar */
                    border-radius: 4px;
                    padding: 12px; 
                    margin-bottom: 15px; 
                    font-size: 9pt;
                }}
                
                /* Identidade visual dos elementos de texto do paciente */
                .patient-name {{ font-weight: bold; font-size: 11pt; text-transform: uppercase; margin-bottom: 8px; color: #000; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
                .patient-info {{ margin-bottom: 3px; color: #333; }}
                .history-title {{ font-weight: bold; margin-top: 8px; margin-bottom: 4px; color: #555; font-size: 8.5pt; }}
                .history-list {{ margin-left: 5px; padding-left: 8px; border-left: 2px solid #ddd; line-height: 1.4; color: #222; }}
                .idx {{ color: #555; font-family: monospace; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 HMPCF - AUDITORIA {titulo_periodo}</h1>
                <p>Top 20 Pacientes - Dados Higienizados (Distinct) | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            
            <div class="container">
                {pacientes_html}
            </div>
        </body>
        </html>
        """

        # --- 8. RENDERIZAÇÃO FINAL ---
        # Pega a "sopa de letrinhas" do HTML e entrega pro WeasyPrint desenhar o PDF físico.
        HTML(string=html_template).write_pdf(arquivo_pdf)
        
        print(f"\n✅ SUCESSO! Relatório PDF gerado e otimizado para impressão.")
        print(f"📁 Arquivo salvo no caminho: {arquivo_pdf}")

    except Exception as e:
        # Se algo de muito errado acontecer (ex: sem permissão para salvar o arquivo), avisa o erro exato
        print(f"\n❌ ERRO FATAL AO PROCESSAR PDF: {e}")

# ==============================================================================
# INÍCIO DO PROGRAMA
# Se você der duplo clique neste arquivo ou rodar pelo terminal, ele entra aqui:
# ==============================================================================
if __name__ == "__main__":
    gerar_auditoria_pdf()