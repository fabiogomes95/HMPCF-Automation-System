import sqlite3
import os

pasta_atual = os.path.dirname(os.path.abspath(__file__))
caminho_db = os.path.join(pasta_atual, 'hospital.db')

print("=========================================")
print("🔍 NOVA BUSCA: PROCURANDO POR NOME...")
print("=========================================\n")

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # Busca flexível: encontra qualquer registro que contenha DIJANETE
    nome_alvo = "%DIJANETE%"

    cursor.execute("SELECT nome, sus, sexo FROM pacientes WHERE nome LIKE ?", (nome_alvo,))
    paciente = cursor.fetchone()

    if paciente:
        nome = paciente[0]
        sus = paciente[1]
        sexo = paciente[2]
        
        print(f"🚨 ACHEI A PACIENTE PELO NOME!")
        print(f"Nome no banco: {nome}")
        print(f"SUS salvo como: [{sus}]  <-- Veja a formatação aqui")
        print(f"👉 VALOR EXATO DO SEXO: [{sexo}]")
    else:
        print(f"❌ VIXE! Nenhuma paciente com 'DIJANETE' no nome foi encontrada.")
        print("Isso significa que o cadastro dela nem chegou a ser salvo nesse hospital.db!")

    conn.close()

except sqlite3.Error as e:
    print(f"Erro no banco: {e}")