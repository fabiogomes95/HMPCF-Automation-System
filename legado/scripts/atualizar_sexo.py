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

Uso: python scripts/atualizar_sexo.py
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger

logger.info("==================================================")
logger.info("SANEAMENTO DE BANCO: ATUALIZACAO DE SEXO PARA 'I'")
logger.info("==================================================")

# Localiza o banco (primeiro na mesma pasta, depois na raiz)
caminho_db = os.path.join(
    os.path.dirname(__file__), 'hospital.db'
)

if not os.path.exists(caminho_db):
    caminho_db = os.path.join(
        os.path.dirname(__file__), '..', 'hospital.db'
    )

if not os.path.exists(caminho_db):
    logger.error(f"ERRO: Banco nao encontrado em: {caminho_db}")
    exit()

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    logger.info("Buscando registros sem sexo definido...")

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

    logger.info(
        f"SUCESSO: {linhas_afetadas} pacientes "
        f"atualizados para 'I' (Indefinido)."
    )
    conn.close()

except sqlite3.Error as e:
    logger.error(f"ERRO NO BANCO DE DADOS: {e}")
