"""
INSPECIONAR_DB.PY — Inspeção de Banco de Dados | Debug de Registros
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
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger

pasta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
caminho_db = os.path.join(pasta_raiz, 'hospital.db')

logger.info("=========================================")
logger.info("NOVA BUSCA: PROCURANDO POR NOME...")
logger.info("=========================================")

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

        logger.info("ACHEI A PACIENTE PELO NOME!")
        logger.info(f"Nome no banco: {nome}")
        logger.info(f"SUS salvo como: [{sus}]")
        logger.info(f"VALOR EXATO DO SEXO: [{sexo}]")
    else:
        logger.info("Nenhuma paciente com o termo especificado foi encontrada.")

    conn.close()

except sqlite3.Error as e:
    logger.error(f"Erro no banco: {e}")
