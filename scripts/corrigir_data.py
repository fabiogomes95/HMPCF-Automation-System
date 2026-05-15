"""
CORRIGIR_DATA.PY — Faxina de Datas Impossíveis no Firebird
============================================================
Eu criei esse script porque o sistema BPA do governo trava
quando encontra datas absurdas tipo "99/99/9999" ou "00/00/0000".

O que ele faz:
1. Conecta no Firebird (BPAMAG.GDB)
2. Varre a tabela CADCNS atrás de datas inválidas
3. Substitui tudo por 01/01/1990 (data padrão segura)
4. Mostra um preview antes de aplicar (segurança)

Uso: python scripts/corrigir_data.py
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import firebirdsql
from datetime import datetime
from logging_setup import logger
from config import FIREBIRD_PATH, FIREBIRD_USER, FIREBIRD_PASSWORD

CAMINHO_GDB = FIREBIRD_PATH
USER = FIREBIRD_USER
PASS = FIREBIRD_PASSWORD
DATA_PADRAO = '19900101'


def corrigir_banco():
    """
    Função principal:
    - Conecta no Firebird
    - Busca registros com datas absurdas
    - Pergunta se pode corrigir (segurança)
    - Aplica a correção se autorizado
    """
    try:
        logger.info(f"Conectando ao banco em: {CAMINHO_GDB}")

        # Abro a conexão com o Firebird
        # charset='WIN1252' porque o BPA usa codificação Windows
        con = firebirdsql.connect(
            host='localhost',
            database=CAMINHO_GDB,
            user=USER,
            password=PASS,
            charset='WIN1252'
        )
        cur = con.cursor()

        # --- PASSO 1: BUSCAR DATAS INVÁLIDAS ---
        # Considero inválidas:
        # - Anteriores a 1890 (ninguém vivo tem mais de 136 anos)
        # - Posteriores a 2026 (ano futuro, não faz sentido)
        # - Nulas/NULL (campo vazio)
        # - "00000000" e "99999999" (placeholders inválidos)
        logger.info("Analisando registros...")

        sql_busca = """
            SELECT CNS, NOME, DTNASC
            FROM CADCNS
            WHERE DTNASC < '18900101'
               OR DTNASC > '20261231'
               OR DTNASC IS NULL
               OR DTNASC = '00000000'
               OR DTNASC = '99999999'
        """

        cur.execute(sql_busca)
        pacientes_com_erro = cur.fetchall()

        if not pacientes_com_erro:
            logger.info("Nenhuma data absurda encontrada! Banco limpo.")
            con.close()
            return

        # --- PASSO 2: PREVIEW DOS DADOS ---
        # Mostro quantos registros problemáticos foram achados
        logger.warning(f"ATENCAO: Encontrados {len(pacientes_com_erro)} pacientes com datas invalidas.")
        logger.info("-" * 50)
        for p in pacientes_com_erro[:10]:
            logger.info(f"PACIENTE: {p[1][:25]} | DATA ATUAL: {p[2]}")
        logger.info("-" * 50)

        # --- PASSO 3: CONFIRMAÇÃO MANUAL ---
        # Só aplico a correção se o usuário digitar 'S'
        # Isso evita estragar o banco por engano
        confirmar = input(
            f"\nDESEJA CORRIGIR TODOS ESSES {len(pacientes_com_erro)} "
            f"REGISTROS PARA {DATA_PADRAO}? (S/N): "
        )

        if confirmar.upper() == 'S':
            logger.info("Corrigindo registros no banco de dados...")

            # UPDATE em lote: mesma condição da busca
            sql_update = f"""
                UPDATE CADCNS
                SET DTNASC = '{DATA_PADRAO}'
                WHERE DTNASC < '18900101'
                   OR DTNASC > '20261231'
                   OR DTNASC IS NULL
                   OR DTNASC = '00000000'
                   OR DTNASC = '99999999'
            """

            cur.execute(sql_update)
            con.commit()  # COMMIT = salva de verdade no banco

            logger.info(f"SUCESSO! {len(pacientes_com_erro)} pacientes atualizados para 01/01/1990.")
        else:
            logger.info("Operacao cancelada. Nada foi alterado.")

        con.close()

    except Exception as e:
        logger.error(f"ERRO AO ACESSAR O BANCO: {e}")


if __name__ == "__main__":
    # Se rodar este arquivo diretamente, executa a correção
    corrigir_banco()
    input("\nPressione Enter para sair...")
