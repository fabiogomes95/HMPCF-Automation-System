# ==============================================================================
# IMPORTADOR EM LOTE COM ATUALIZAÇÃO CIRÚRGICA (SMART UPDATE)
# ==============================================================================
# OBJETIVO:
# Este script varre uma pasta em busca de planilhas CSV da recepção.
# Ele lê cada paciente e cruza o Cartão do SUS com o banco de dados (hospital.db).
# - Se o paciente NÃO existe: Cadastra do zero.
# - Se o paciente JÁ existe: Ele verifica se a ficha antiga estava em branco. 
#   Se sim, atualiza e enriquece os dados, sem apagar o histórico!
# ==============================================================================

import sqlite3  
import csv      
import os       
import sys      
import glob     # Biblioteca que permite caçar múltiplos arquivos de uma vez (*.csv).
from datetime import datetime 

# --- Importação Módulos Locais ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from utils import apenas_numeros, valida_cns
except ImportError:
    print("❌ ERRO CRÍTICO: 'apenas_numeros' e 'valida_cns' não foram encontrados no utils.")
    exit()

# ==============================================================================
# 1. FUNÇÃO DEFENSIVA
# ==============================================================================
def pega_coluna_segura(linha, indice):
    """
    Previne que o Python trave com erro de 'IndexError' caso o arquivo do Excel 
    esteja corrompido ou tenha cortado as últimas colunas da planilha.
    """
    if len(linha) > indice:
        return linha[indice].strip()
    return ""

def executar_importacao_lote():
    print("=========================================================")
    print("📥 IMPORTADOR EM LOTE RECEPÇÃO -> HOSPITAL.DB")
    print("🧠 MODO INTELIGENTE + RELATÓRIO TXT DE AUDITORIA")
    print("=========================================================\n")

    # ==========================================================================
    # 2. LOCALIZANDO ARQUIVOS (O MOTOR DE LOTE)
    # ==========================================================================
    caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')
    if not os.path.exists(caminho_db):
        caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')

    arquivos_csv = glob.glob("*.csv")
    
    # Filtro: Ignora a planilha do robô do BPA que possa estar na pasta
    arquivos_csv = [arq for arq in arquivos_csv if arq.lower() != "pacientes.csv"]
    
    if not arquivos_csv:
        print("❌ Nenhum arquivo CSV da recepção encontrado na pasta.")
        return
        
    print(f"📁 Encontrados {len(arquivos_csv)} arquivos CSV para processar!")
    separador = input("👉 Os arquivos usam vírgula (,) ou ponto e vírgula (;)? ").strip()
    if separador not in [',', ';']: separador = ';'

    # Variáveis de Estatística
    inseridos_novos, atualizados_parciais, intactos_perfeitos, ignorados_erro = 0, 0, 0, 0
    detalhes_novos = []

    try:
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()
        print("\n⏳ Iniciando varredura das planilhas...\n")

        # ======================================================================
        # 3. EXTRAÇÃO E TRATAMENTO
        # ======================================================================
        for arquivo in arquivos_csv:
            print(f"🔄 Lendo planilha: {arquivo}...")
            
            with open(arquivo, mode='r', encoding='utf-8', errors='ignore') as f:
                leitor = csv.reader(f, delimiter=separador)
                next(leitor, None) # Pula o cabeçalho
                
                for linha in leitor:
                    if len(linha) < 10: continue
                    
                    # Limpeza no ato da extração
                    nome_csv = pega_coluna_segura(linha, 1).upper()
                    dn_csv   = pega_coluna_segura(linha, 2)
                    sexo_csv = pega_coluna_segura(linha, 4).upper()
                    cpf_csv  = apenas_numeros(pega_coluna_segura(linha, 8))
                    sus_csv  = apenas_numeros(pega_coluna_segura(linha, 9))
                    
                    # Trava Matemática
                    if not sus_csv or not valida_cns(sus_csv):
                        ignorados_erro += 1
                        continue

                    # ==========================================================
                    # 4. LÓGICA DE NEGÓCIO (O SMART UPDATE)
                    # ==========================================================
                    cursor.execute("SELECT cpf, nome, dn, sexo FROM pacientes WHERE sus = ?", (sus_csv,))
                    paciente_banco = cursor.fetchone()
                    
                    if paciente_banco:
                        db_cpf, db_nome, db_dn, db_sexo = paciente_banco
                        campos_para_atualizar, valores_para_atualizar = [], []
                        
                        # Verifica CPF (Se no banco tá vazio, mas chegou o CPF agora, injeta)
                        if (not db_cpf or db_cpf.strip() == "") and cpf_csv:
                            campos_para_atualizar.append("cpf = ?")
                            valores_para_atualizar.append(cpf_csv)
                            
                        # Verifica Nome
                        if (not db_nome or db_nome.strip() == "") and nome_csv:
                            campos_para_atualizar.append("nome = ?")
                            valores_para_atualizar.append(nome_csv)
                            
                        # Verifica Data
                        if (not db_dn or db_dn.strip() == "") and dn_csv:
                            campos_para_atualizar.append("dn = ?")
                            valores_para_atualizar.append(dn_csv)
                            
                        # Verifica Sexo
                        if (not db_sexo or db_sexo.strip() == "") and sexo_csv in ['M', 'F', 'I']:
                            campos_para_atualizar.append("sexo = ?")
                            valores_para_atualizar.append(sexo_csv)
                            
                        if campos_para_atualizar:
                            sql_update = f"UPDATE pacientes SET {', '.join(campos_para_atualizar)} WHERE sus = ?"
                            valores_para_atualizar.append(sus_csv)
                            try:
                                cursor.execute(sql_update, valores_para_atualizar)
                                atualizados_parciais += 1
                            except sqlite3.IntegrityError:
                                ignorados_erro += 1
                        else:
                            intactos_perfeitos += 1
                    else:
                        # --- PACIENTE NOVO (INSERT) ---
                        try:
                            cursor.execute('''
                                INSERT INTO pacientes (sus, cpf, nome, dn, sexo)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (sus_csv, cpf_csv, nome_csv, dn_csv, sexo_csv))
                            inseridos_novos += 1
                            detalhes_novos.append(f"NOME: {nome_csv} | SUS: {sus_csv}")
                        except sqlite3.IntegrityError:
                            ignorados_erro += 1

        conn.commit()
        conn.close()

        # ======================================================================
        # 5. LOG E AUDITORIA FINAL
        # ======================================================================
        if detalhes_novos:
            nome_relatorio = "relatorio_importacao.txt"
            with open(nome_relatorio, "w", encoding="utf-8") as f_txt:
                f_txt.write(f"RELATÓRIO DE NOVOS PACIENTES CADASTRADOS\n")
                f_txt.write(f"DATA DO PROCESSAMENTO: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                f_txt.write("-" * 60 + "\n")
                for registro in detalhes_novos:
                    f_txt.write(registro + "\n")
            print(f"\n📄 Auditoria salva! Relatório detalhado gerado em: '{nome_relatorio}'")

        print("\n=========================================================")
        print("✅ PROCESSAMENTO EM LOTE CONCLUÍDO COM SUCESSO!")
        print("=========================================================")
        print(f"📁 Arquivos lidos: {len(arquivos_csv)}")
        print(f"➕ Novos pacientes (Do zero): {inseridos_novos}")
        print(f"💉 Atualizados (Preencheu apenas o que faltava): {atualizados_parciais}")
        print(f"🛡 Cadastros intactos (Já estavam 100% completos): {intactos_perfeitos}")
        print(f"🚫 Ignorados (Erros SUS ou Duplicidade): {ignorados_erro}")
        print("=========================================================")

    except Exception as e:
        print(f"\n❌ Ocorreu um erro durante a importação: {e}")

if __name__ == "__main__":
    executar_importacao_lote()
