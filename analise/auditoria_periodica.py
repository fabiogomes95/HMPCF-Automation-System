# ==============================================================================
# 📄 GERADOR DE AUDITORIA PERIÓDICA (HMPCF)
# ==============================================================================
# OBJETIVO:
# 1. Filtrar atendimentos por período (Mensal, Trimestral ou Semestral).
# 2. Identificar os pacientes com maior frequência de visitas.
# 3. Exportar um relatório .txt formatado para conferência de auditoria.
# ==============================================================================

import os
import sqlite3
import sys
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E BLINDAGEM DE ROTAS
# ==============================================================================
pasta_atual = os.path.dirname(os.path.abspath(__file__))
# 🎯 CORREÇÃO: Força o Python a subir um nível ('..') para a pasta raiz
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))
caminho_db = os.path.join(pasta_pai, 'hospital.db')

def calcular_data_inicio(meses):
    """Calcula a data de início baseada no período escolhido."""
    hoje = datetime.now()
    # Aproximação simples: 1 mês = 30 dias
    return (hoje - timedelta(days=meses * 30)).strftime('%Y-%m-%d')

def gerar_relatorio_txt():
    print("==================================================")
    print("📑 GERADOR DE RELATÓRIO DE AUDITORIA")
    print("==================================================\n")

    # 1. ESCOLHA DO PERÍODO
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
    
    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: Banco de dados não encontrado em: {caminho_db}")
        return

    try:
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()

        # 2. BUSCA DOS TOP 20 PACIENTES DO PERÍODO
        # Filtramos pela data e contamos os atendimentos
        query_top = """
            SELECT sus, COUNT(*) as total 
            FROM atendimentos 
            WHERE date(data_atendimento) >= date(?)
            AND sus != '' AND sus IS NOT NULL
            GROUP BY sus 
            ORDER BY total DESC 
            LIMIT 20
        """
        cursor.execute(query_top, (data_limite,))
        top_pacientes = cursor.fetchall()

        if not top_pacientes:
            print("\n⚠️ Nenhum atendimento encontrado no período selecionado.")
            return

        # 3. CRIAÇÃO DO ARQUIVO TXT
        nome_arquivo = f"RELATORIO_AUDITORIA_{opcao}_MESES.txt"
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write("==================================================\n")
            f.write(f"HMPCF - RELATÓRIO DE AUDITORIA ({opcao} MESES)\n")
            f.write(f"GERADO EM: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write("==================================================\n\n")

            for sus_alvo, total in top_pacientes:
                # Busca os dados cadastrais do paciente
                cursor.execute("SELECT nome, cpf, sus FROM pacientes WHERE sus = ?", (sus_alvo,))
                p = cursor.fetchone()
                
                if not p: continue
                
                nome, cpf, sus = p
                
                # Busca o histórico detalhado do período
                cursor.execute("""
                    SELECT data_atendimento, hora_atendimento 
                    FROM atendimentos 
                    WHERE sus = ? AND date(data_atendimento) >= date(?)
                    ORDER BY data_atendimento DESC, hora_atendimento DESC
                """, (sus_alvo, data_limite))
                historico = cursor.fetchall()

                # ESCREVE O BLOCO FORMATADO
                f.write("==================================================\n")
                f.write("📋 RELATÓRIO DE HISTÓRICO DO PACIENTE\n")
                f.write("==================================================\n")
                f.write(f"👤 NOME: {nome}\n")
                f.write(f"💳 CPF : {cpf if cpf else 'NÃO INFORMADO'}\n")
                f.write(f"🏥 SUS : {sus}\n")
                f.write(f"🔄 TOTAL DE ENTRADAS: {len(historico)} vez(es)\n")
                f.write("--------------------------------------------------\n")
                f.write("📅 LINHA DO TEMPO DE ATENDIMENTOS:\n")
                
                for i, (data, hora) in enumerate(historico, start=1):
                    # Tenta formatar a data de YYYY-MM-DD para DD/MM/YYYY
                    try:
                        d_fmt = datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        d_fmt = data
                    
                    f.write(f"   [{i:02d}] ➜ Data: {d_fmt} às {hora}\n")
                
                f.write("==================================================\n\n\n")

        print(f"\n✅ SUCESSO! Relatório gerado: '{nome_arquivo}'")
        print(f"Total de {len(top_pacientes)} pacientes processados.")

    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    gerar_relatorio_txt()