import sqlite3
import os

print("==================================================")
print("🛠️ SANEAMENTO DE BANCO: ATUALIZAÇÃO DE SEXO PARA 'I'")
print("==================================================\n")

# Caminho apontando para o seu banco de dados
caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')

# Tenta achar o banco um nível acima caso o script esteja na pasta de automação
if not os.path.exists(caminho_db):
    caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')

if not os.path.exists(caminho_db):
    print(f"❌ ERRO: O banco de dados não foi encontrado no caminho: {caminho_db}")
    exit()

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    print("🔍 Buscando registros sem sexo definido ou diferente de M/F...")
    
    # Atualiza para 'I' qualquer registro que seja nulo, vazio ou diferente de M, F e I
    cursor.execute("""
        UPDATE pacientes 
        SET sexo = 'I' 
        WHERE sexo IS NULL 
           OR TRIM(UPPER(sexo)) NOT IN ('M', 'F', 'I')
           OR TRIM(sexo) = ''
    """)
    
    linhas_afetadas = cursor.rowcount
    conn.commit()
    
    print(f"✅ SUCESSO: {linhas_afetadas} pacientes atualizados para 'I' (Indefinido).")
    
    conn.close()
except sqlite3.Error as e:
    print(f"❌ ERRO NO BANCO DE DADOS: {e}")