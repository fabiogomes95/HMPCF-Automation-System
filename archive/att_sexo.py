# ==============================================================================
# FERRAMENTA DE MANUTENÇÃO - ATUALIZAÇÃO EM MASSA (UPDATE)
# ==============================================================================
# OBJETIVO:
# Este script varre o banco de dados e corrige um erro comum na recepção:
# O esquecimento do preenchimento do sexo. Ele atualiza automaticamente
# registros nulos ou inválidos para 'I' (Indefinido), garantindo que
# o sistema do Governo (BPA) não rejeite a ficha no faturamento.
# ==============================================================================

import sqlite3  # Para interagir com o banco de dados SQL.
import os       # Para navegar pelas pastas do sistema.

print("==================================================")
print("🛠 SANEAMENTO DE BANCO: ATUALIZAÇÃO DE SEXO PARA 'I'")
print("==================================================\n")

# ==============================================================================
# 1. LOCALIZAÇÃO DINÂMICA DO BANCO DE DADOS
# ==============================================================================
# Primeiro tenta achar o banco na mesma pasta. Se não achar, volta uma pasta ('..')
caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')

if not os.path.exists(caminho_db):
    caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')

if not os.path.exists(caminho_db):
    print(f"❌ ERRO: O banco de dados não foi encontrado no caminho: {caminho_db}")
    exit()

try:
    # ==========================================================================
    # 2. CONEXÃO E EXECUÇÃO DA QUERY (SQL CIRÚRGICO)
    # ==========================================================================
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()
    
    print("🔍 Buscando registros sem sexo definido ou diferente de M/F...")
    
    # A lógica SQL: O comando TRIM remove espaços vazios acidentais e o UPPER
    # transforma tudo em maiúsculo. Se o resultado não for M, F ou I, ou se
    # for vazio (NULL), ele força a letra 'I'.
    cursor.execute("""
        UPDATE pacientes 
        SET sexo = 'I' 
        WHERE sexo IS NULL 
           OR TRIM(UPPER(sexo)) NOT IN ('M', 'F', 'I') 
           OR TRIM(sexo) = ''
    """)
    
    # rowcount nos diz exatamente quantas linhas foram alteradas por esse UPDATE
    linhas_afetadas = cursor.rowcount 
    
    # O commit é quem realmente salva a alteração física no arquivo hospital.db
    conn.commit() 
    
    print(f"✅ SUCESSO: {linhas_afetadas} pacientes atualizados para 'I' (Indefinido).")
    conn.close()

except sqlite3.Error as e:
    # Tratamento de erro elegante para o banco não travar o sistema
    print(f"❌ ERRO NO BANCO DE DADOS: {e}")
