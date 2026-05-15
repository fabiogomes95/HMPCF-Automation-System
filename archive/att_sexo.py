"""
ATT_SEXO.PY — Atualização em Massa de Sexo no SQLite
======================================================
Corrige um erro comum na recepção: o esquecimento do sexo.

Varre o banco e atualiza pra 'I' (Indefinido) todo registro
onde o sexo for:
- NULL (não preenchido)
- Vazio
- Diferente de M, F ou I

Isso garante que o sistema BPA do governo não rejeite a ficha.

Uso: python archive/att_sexo.py
"""

import sqlite3
import os

print("==================================================")
print("SANEAMENTO DE BANCO: ATUALIZACAO DE SEXO PARA 'I'")
print("==================================================\n")

# Localiza o banco (primeiro na mesma pasta, depois na raiz)
caminho_db = os.path.join(
    os.path.dirname(__file__), 'hospital.db'
)

if not os.path.exists(caminho_db):
    caminho_db = os.path.join(
        os.path.dirname(__file__), '..', 'hospital.db'
    )

if not os.path.exists(caminho_db):
    print(f"ERRO: Banco nao encontrado em: {caminho_db}")
    exit()

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    print("Buscando registros sem sexo definido...")

    # Query: atualiza sexo pra 'I' onde for inválido
    cursor.execute("""
        UPDATE pacientes
        SET sexo = 'I'
        WHERE sexo IS NULL
           OR TRIM(UPPER(sexo)) NOT IN ('M', 'F', 'I')
           OR TRIM(sexo) = ''
    """)

    linhas_afetadas = cursor.rowcount
    conn.commit()

    print(
        f"SUCESSO: {linhas_afetadas} pacientes "
        f"atualizados para 'I' (Indefinido)."
    )
    conn.close()

except sqlite3.Error as e:
    print(f"ERRO NO BANCO DE DADOS: {e}")
