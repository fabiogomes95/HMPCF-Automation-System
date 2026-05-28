"""
HISTORICO_PACIENTE.PY — Lupa do Auditor | Busca de Histórico do Paciente
==========================================================================
Busca histórico completo de atendimentos por NOME, CPF ou SUS.

Uso direto:  python historico_paciente.py
Via Eel:     analise_buscar_historico("nome ou CPF ou SUS")
"""

import os
import sqlite3
import sys
from datetime import datetime

pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))

if pasta_pai not in sys.path:
    sys.path.append(pasta_pai)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger

try:
    from utils import apenas_numeros, remove_accents
except ImportError as e:
    msg = f"ERRO: Nao foi possivel importar o utils.py. Motivo: {e}"
    logger.error(msg)


def buscar_por_termo(termo_busca: str) -> str:
    """
    Busca histórico completo por NOME, CPF ou SUS.
    termo_busca: string com nome, CPF ou SUS.
    Retorna string formatada com resultados.
    """
    if not termo_busca:
        return "Busca cancelada (termo vazio)."

    termo_numero = apenas_numeros(termo_busca)
    termo_texto = remove_accents(termo_busca).upper()
    busca_num = termo_numero if termo_numero != "" else "NUMERO_IMPOSSIVEL"
    busca_nome = f"%{termo_texto}%" if termo_texto != "" else "NOME_IMPOSSIVEL"

    caminho_db = os.path.join(pasta_pai, 'hospital.db')
    if not os.path.exists(caminho_db):
        msg = f"ERRO: Banco nao encontrado em:\n{caminho_db}"
        logger.error(msg)
        return msg

    try:
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()
        query = """
            SELECT p.nome, p.cpf, p.sus,
                   a.data_atendimento, a.hora_atendimento, a.procedencia
            FROM pacientes p
            JOIN atendimentos a ON
                (REPLACE(REPLACE(p.cpf, '.', ''), '-', '')
                 = REPLACE(REPLACE(a.cpf, '.', ''), '-', '')
                 AND p.cpf != '' AND p.cpf IS NOT NULL)
                OR
                (REPLACE(REPLACE(REPLACE(p.sus, '.', ''), '-', ''), ' ', '')
                 = REPLACE(REPLACE(REPLACE(a.sus, '.', ''), '-', ''), ' ', '')
                 AND p.sus != '' AND p.sus IS NOT NULL)
            WHERE
                REPLACE(REPLACE(p.cpf, '.', ''), '-', '') = ?
                OR
                REPLACE(REPLACE(REPLACE(p.sus, '.', ''), '-', ''), ' ', '') = ?
                OR
                p.nome LIKE ?
            ORDER BY a.data_atendimento DESC, a.hora_atendimento DESC
        """
        cursor.execute(query, (busca_num, busca_num, busca_nome))
        resultados = cursor.fetchall()
        conn.close()

        if not resultados:
            msg = ("NENHUM ATENDIMENTO ENCONTRADO para este paciente.\n"
                   "Verifique se o nome/documento esta correto ou se ele ja foi atendido na unidade.")
            logger.warning(msg)
            return msg

        nome_paciente = resultados[0][0]
        cpf_paciente = resultados[0][1]
        sus_paciente = resultados[0][2]
        total_visitas = len(resultados)

        linhas = []
        linhas.append("=" * 50)
        linhas.append("RELATORIO DE HISTORICO DO PACIENTE")
        linhas.append("=" * 50)
        linhas.append(f"NOME: {nome_paciente}")
        linhas.append(f"CPF : {cpf_paciente if cpf_paciente else 'NAO INFORMADO'}")
        linhas.append(f"SUS : {sus_paciente if sus_paciente else 'NAO INFORMADO'}")
        linhas.append(f"TOTAL DE ENTRADAS: {total_visitas} vez(es)")
        linhas.append("-" * 50)
        linhas.append("LINHA DO TEMPO DE ATENDIMENTOS:")

        for i, linha in enumerate(resultados, start=1):
            data_raw = linha[3]
            hora_raw = linha[4]
            procedencia = linha[5]
            try:
                if data_raw and '-' in data_raw:
                    data_br = datetime.strptime(data_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                else:
                    data_br = data_raw
            except ValueError:
                data_br = data_raw
            proc_texto = f" (Via: {procedencia})" if procedencia and procedencia.upper() != "NORMAL" else ""
            linhas.append(f"   [{i:02d}] -> Data: {data_br} as {hora_raw}{proc_texto}")

        linhas.append("=" * 50 + "\n")
        resultado = "\n".join(linhas)
        logger.info(resultado)
        return resultado

    except sqlite3.Error as e:
        msg = f"ERRO FATAL NO BANCO DE DADOS: {e}"
        logger.error(msg)
        return msg


if __name__ == "__main__":
    logger.info("==================================================")
    logger.info("LUPA DO AUDITOR - HISTORICO DE PACIENTES")
    logger.info("==================================================")
    while True:
        termo = input("Digite o NOME, CPF ou SUS do paciente: ").strip()
        buscar_por_termo(termo)
        continuar = input("Pesquisar outro paciente? (S/N): ").strip().upper()
        if continuar != 'S':
            logger.info("Encerrando Lupa do Auditor.")
            break
