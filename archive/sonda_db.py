# ==============================================================================
# SCRIPT DE DEBUGGING (SONDA DE BANCO DE DADOS)
# ==============================================================================
# OBJETIVO:
# Uma ferramenta leve e direta via terminal para desenvolvedores conferirem
# rapidamente como um dado específico foi gravado fisicamente nas tabelas 
# do SQLite (ex: formatado com espaços, nulo, ou preenchido corretamente).
# ==============================================================================

import sqlite3
import os

# Mapeia a localização do banco
pasta_atual = os.path.dirname(os.path.abspath(__file__))
caminho_db = os.path.join(pasta_atual, 'hospital.db')

print("=========================================")
print("🔍 NOVA BUSCA: PROCURANDO POR NOME...")
print("=========================================\n")

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()
    
    # A cláusula SQL "LIKE" acompanhada dos "%" funciona como uma busca flexível.
    # %DIJANETE% vai encontrar "MARIA DIJANETE" ou "DIJANETE SILVA".
    nome_alvo = "%DIJANETE%"
    
    cursor.execute("SELECT nome, sus, sexo FROM pacientes WHERE nome LIKE ?", (nome_alvo,))
    paciente = cursor.fetchone() # Traz apenas o primeiro resultado que ele achar
    
    if paciente:
        # Desempacota a Tupla devolvida pelo SQLite
        nome, sus, sexo = paciente
        
        # O uso das chaves/colchetes na tela ajuda a ver se o texto foi salvo 
        # com espaços inúteis, ex: [ M ] ou [M].
        print(f"🚨 ACHEI A PACIENTE PELO NOME!")
        print(f"Nome no banco: {nome}")
        print(f"SUS salvo como: [{sus}]  <-- Veja a formatação aqui")
        print(f"👉 VALOR EXATO DO SEXO: [{sexo}]")
    else:
        print(f"❌ VIXE! Nenhuma paciente com o termo especificado foi encontrada.")
        print("Isso significa que o cadastro dela nem chegou a ser salvo no banco!")

    conn.close()

except sqlite3.Error as e:
    print(f"Erro no banco: {e}")