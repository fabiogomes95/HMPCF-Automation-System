"""
CORRIGIR_NULLS.PY — Aniquilador de NULLs no Firebird
=========================================================
O sistema BPA do governo TRAVA quando encontra campos NULL
no banco, gerando o erro "UDFLIB".

Esse script resolve o problema de uma vez:
1. Conecta no Firebird (BPAMAG.GDB)
2. Examina a estrutura da tabela CADCNS
3. Descobre quais colunas são TEXTO e quais são NÚMERO
4. Substitui NULL por '' (texto) ou 0 (número)
5. É 100% automático — não preciso saber os nomes das colunas

Ele lê os metadados do Firebird (RDB$RELATION_FIELDS) pra
descobrir os tipos de cada coluna dinamicamente.
"""

import firebirdsql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import FIREBIRD_USER, FIREBIRD_PASSWORD


def aniquilar_nulls_bpa(caminho_gdb=""):
    """
    Varre TODAS as colunas da tabela CADCNS e substitui NULLs.
    
    Parâmetros:
        caminho_gdb: caminho do arquivo .GDB do Firebird
    
    A lógica:
    - Colunas de texto (tipos 14, 37, 40) → '' (string vazia)
    - Colunas numéricas (tipos 7, 8, 10, 16, 27) → 0
    
    Retorna relatório com quantos NULLs foram corrigidos.
    """
    if not caminho_gdb:
        return "Erro: Nenhum arquivo .gdb informado."

    try:
        conexao = firebirdsql.connect(
            host='localhost',
            database=caminho_gdb,
            user=FIREBIRD_USER,
            password=FIREBIRD_PASSWORD,
            charset='ISO8859_1'
        )
        cursor = conexao.cursor()

        # --- DESCOBRE A ESTRUTURA DA TABELA ---
        # Consulto os metadados do Firebird pra pegar:
        # - Nome da coluna (RDB$FIELD_NAME)
        # - Tipo da coluna (RDB$FIELD_TYPE)
        query_colunas = """
            SELECT f.RDB$FIELD_NAME, t.RDB$FIELD_TYPE
            FROM RDB$RELATION_FIELDS f
            JOIN RDB$FIELDS t ON f.RDB$FIELD_SOURCE = t.RDB$FIELD_NAME
            WHERE f.RDB$RELATION_NAME = 'CADCNS'
        """
        cursor.execute(query_colunas)
        colunas = cursor.fetchall()

        buracos_texto = 0   # NULLs em colunas de texto
        buracos_numero = 0  # NULLs em colunas numéricas

        for row in colunas:
            coluna = str(row[0]).strip()
            tipo = row[1]

            sql_update = ""

            # Tipos de texto no Firebird:
            # 14 = CHAR, 37 = VARCHAR, 40 = CSTRING
            if tipo in (14, 37, 40):
                sql_update = (
                    f"UPDATE CADCNS SET {coluna} = '' "
                    f"WHERE {coluna} IS NULL"
                )
            # Tipos numéricos no Firebird:
            # 7 = SMALLINT, 8 = INTEGER, 10 = FLOAT,
            # 16 = BIGINT, 27 = DOUBLE PRECISION
            elif tipo in (7, 8, 10, 16, 27):
                sql_update = (
                    f"UPDATE CADCNS SET {coluna} = 0 "
                    f"WHERE {coluna} IS NULL"
                )

            if sql_update:
                try:
                    cursor.execute(sql_update)
                    if tipo in (14, 37, 40):
                        buracos_texto += cursor.rowcount
                    else:
                        buracos_numero += cursor.rowcount
                except Exception:
                    # Se der erro numa coluna específica, pulo
                    pass

        conexao.commit()

        msg = (
            f"Aniquilacao Concluida!\n"
            f"Campos de Texto corrigidos: {buracos_texto}\n"
            f"Campos Numericos corrigidos: {buracos_numero}"
        )
        return msg

    except Exception as e:
        return f"Erro na execucao: {e}"

    finally:
        if 'conexao' in locals():
            conexao.close()


if __name__ == "__main__":
    gdb = input("Caminho do .gdb: ").strip()
    print(aniquilar_nulls_bpa(gdb))
