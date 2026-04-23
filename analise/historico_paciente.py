# ==============================================================================
# 🔍 LUPA DO AUDITOR: HISTÓRICO DE ATENDIMENTOS DO PACIENTE
# ==============================================================================

import os
import sqlite3
import sys
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E BLINDAGEM DE ROTAS
# ==============================================================================
pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))

if pasta_atual not in sys.path: sys.path.append(pasta_atual)
if pasta_pai not in sys.path: sys.path.append(pasta_pai)

try:
    from utils import apenas_numeros, remove_accents
except ImportError as e:
    print(f"❌ ERRO: Não foi possível importar o utils.py. Motivo: {e}")
    exit()

# ==============================================================================
# MOTOR DE BUSCA
# ==============================================================================
def buscar_historico():
    print("==================================================")
    print("🔍 LUPA DO AUDITOR - HISTÓRICO DE PACIENTES")
    print("==================================================\n")

    # 1. ENTRADA DE DADOS
    termo_busca = input("👉 Digite o NOME, CPF ou SUS do paciente: ").strip()
    
    if not termo_busca:
        print("🛑 Busca cancelada. Nenhum termo digitado.")
        return

    # 2. INTELIGÊNCIA DE HIGIENIZAÇÃO
    termo_numero = apenas_numeros(termo_busca)
    termo_texto = remove_accents(termo_busca).upper()

    # 🛡️ TRAVA 1: PREVENÇÃO DA STRING VAZIA (O BUG DOS 123 REGISTROS)
    # Se o usuário não digitou números, passamos um valor impossível de achar no banco.
    # Assim, o SQL nunca vai pesquisar por "campos vazios".
    busca_num = termo_numero if termo_numero != "" else "NUMERO_IMPOSSIVEL"
    busca_nome = f"%{termo_texto}%" if termo_texto != "" else "NOME_IMPOSSIVEL"

    caminho_db = os.path.join(pasta_pai, 'hospital.db')
    
    if not os.path.exists(caminho_db):
        print(f"❌ ERRO: Banco de dados não encontrado em:\n{caminho_db}")
        return

    try:
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()

        # 🛡️ TRAVA 2: SQL COM IGNORADOR DE MÁSCARAS (O BUG DO CPF NÃO ENCONTRADO)
        # O comando REPLACE varre o banco temporariamente arrancando pontos e traços 
        # para que o cruzamento e a pesquisa sejam feitos apenas com números puros.
        query = """
            SELECT p.nome, p.cpf, p.sus, a.data_atendimento, a.hora_atendimento, a.procedencia
            FROM pacientes p
            JOIN atendimentos a ON 
                (REPLACE(REPLACE(p.cpf, '.', ''), '-', '') = REPLACE(REPLACE(a.cpf, '.', ''), '-', '') AND p.cpf != '' AND p.cpf IS NOT NULL) 
                OR 
                (REPLACE(REPLACE(REPLACE(p.sus, '.', ''), '-', ''), ' ', '') = REPLACE(REPLACE(REPLACE(a.sus, '.', ''), '-', ''), ' ', '') AND p.sus != '' AND p.sus IS NOT NULL)
            WHERE 
                REPLACE(REPLACE(p.cpf, '.', ''), '-', '') = ? 
                OR 
                REPLACE(REPLACE(REPLACE(p.sus, '.', ''), '-', ''), ' ', '') = ? 
                OR 
                p.nome LIKE ?
            ORDER BY a.data_atendimento DESC, a.hora_atendimento DESC
        """
        
        # Executa a busca
        cursor.execute(query, (busca_num, busca_num, busca_nome))
        resultados = cursor.fetchall()
        
        conn.close()

        # 5. EXIBIÇÃO E FORMATAÇÃO DE RESULTADOS
        if not resultados:
            print("\n❌ NENHUM ATENDIMENTO ENCONTRADO para este paciente.")
            print("Verifique se o nome/documento está correto ou se ele já foi atendido na unidade.")
            return

        nome_paciente = resultados[0][0]
        cpf_paciente = resultados[0][1]
        sus_paciente = resultados[0][2]
        total_visitas = len(resultados)

        print("\n" + "="*50)
        print("📋 RELATÓRIO DE HISTÓRICO DO PACIENTE")
        print("="*50)
        print(f"👤 NOME: {nome_paciente}")
        print(f"💳 CPF : {cpf_paciente if cpf_paciente else 'NÃO INFORMADO'}")
        print(f"🏥 SUS : {sus_paciente if sus_paciente else 'NÃO INFORMADO'}")
        print(f"🔄 TOTAL DE ENTRADAS: {total_visitas} vez(es)")
        print("-" * 50)
        print("📅 LINHA DO TEMPO DE ATENDIMENTOS:")
        
        for i, linha in enumerate(resultados, start=1):
            data_raw = linha[3] 
            hora_raw = linha[4] 
            procedencia = linha[5] 
            
            try:
                if data_raw and '-' in data_raw:
                    data_br = datetime.strptime(data_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                else:
                    data_br = data_raw 
            except ValueError:
                data_br = data_raw

            proc_texto = f" (Via: {procedencia})" if procedencia and procedencia.upper() != "NORMAL" else ""
            print(f"   [{i:02d}] ➜ Data: {data_br} às {hora_raw}{proc_texto}")
            
        print("="*50 + "\n")

    except sqlite3.Error as e:
        print(f"\n❌ ERRO FATAL NO BANCO DE DADOS: {e}")

if __name__ == "__main__":
    while True:
        buscar_historico()
        continuar = input("Pesquisar outro paciente? (S/N): ").strip().upper()
        if continuar != 'S':
            print("🚀 Encerrando Lupa do Auditor. Bom trabalho!")
            break