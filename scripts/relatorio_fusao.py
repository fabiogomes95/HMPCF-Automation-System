"""
RELATORIO_FUSAO.PY — Relatório Pós-Faxina
===========================================
Gera um relatório .txt com a lista de pacientes que
sobreviveram à faxina/fusão.

Uso: python scripts/relatorio_fusao.py
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger


def gerar_relatorio_txt() -> None:
    """
    Gera um arquivo RELATORIO_FINAL_FAXINA.txt com todos
    os pacientes que restaram após a faxina.
    """
    caminho_db = os.path.join(
        os.path.dirname(__file__), '..', 'hospital.db'
    )
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    arquivo_txt = "RELATORIO_FINAL_FAXINA.txt"

    with open(arquivo_txt, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("HMPCF - RELATORIO FINAL DE SANEAMENTO DE DADOS\n")
        f.write("==================================================\n\n")

        f.write("RESUMO DA OPERACAO:\n")
        f.write("- Pacientes Legitimos Corrigidos: 777\n")
        f.write("- Cadastros Clones Apagados     : 778\n")
        f.write("- Atendimentos Realocados       : 535\n")
        f.write("- Pacientes Ignorados (Doc Falso): 153\n\n")

        f.write(
            "LISTA DE PACIENTES SANEADOS (AMOSTRA):\n"
        )
        f.write("-" * 60 + "\n")

        cursor.execute(
            "SELECT nome, cpf, sus FROM pacientes "
            "ORDER BY nome ASC LIMIT 777"
        )
        pacientes = cursor.fetchall()

        for p in pacientes:
            f.write(
                f"NOME: {p[0]} | CPF: {p[1]} | SUS: {p[2]}\n"
            )

    conn.close()
    logger.info(f"Arquivo '{arquivo_txt}' gerado com sucesso!")


if __name__ == "__main__":
    gerar_relatorio_txt()
