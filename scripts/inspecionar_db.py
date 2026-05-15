"""
SONDA_DB.PY — Sonda de Banco de Dados | Debug de Registros
===========================================================
Uma ferramenta leve pra desenvolvedor conferir rapidamente
como um registro específico foi salvo no banco SQLite.

Serve pra diagnosticar problemas como:
- Espaços extras no nome
- Formatação incorreta do SUS
- Campo sexo vazio

Uso: python scripts/inspecionar_db.py
(Edite o nome_alvo na linha 27 antes de rodar)
"""

import sqlite3
import os

pasta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
caminho_db = os.path.join(pasta_raiz, 'hospital.db')

print("=========================================")
print("NOVA BUSCA: PROCURANDO POR NOME...")
print("=========================================\n")

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # Nome alvo da busca (EDITAR AQUI pra procurar outro paciente)
    nome_alvo = "%DIJANETE%"

    cursor.execute(
        "SELECT nome, sus, sexo FROM pacientes WHERE nome LIKE ?",
        (nome_alvo,)
    )
    paciente = cursor.fetchone()

    if paciente:
        nome, sus, sexo = paciente

        print("ACHEI A PACIENTE PELO NOME!")
        print(f"Nome no banco: {nome}")
        print(f"SUS salvo como: [{sus}]")
        print(f"VALOR EXATO DO SEXO: [{sexo}]")
    else:
        print(
            "Nenhuma paciente com o termo especificado "
            "foi encontrada."
        )

    conn.close()

except sqlite3.Error as e:
    print(f"Erro no banco: {e}")
