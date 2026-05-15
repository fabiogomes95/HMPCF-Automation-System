"""
DUPLICATAS_GDB.PY — Caçador de Duplicatas no Firebird
=======================================================
O sistema BPA acumulou DUPLICATAS ao longo dos anos — pacientes
com o mesmo Cartão SUS mas em múltiplos registros.

Esse script:
1. Agrupa pacientes pelo Cartão SUS (CNS)
2. Dentro de cada grupo, dá uma PONTUAÇÃO pra cada ficha
3. Mantém a ficha com MAIOR pontuação (mais dados preenchidos)
4. Remove as fichas inferiores

Sistema de pontuação:
- CPF preenchido = 5 pontos (muito mais confiável)
- Endereço preenchido = 1 ponto
- Telefone preenchido = 1 ponto

Usa RDB$DB_KEY (chave física do Firebird) pra deletar
os registros duplicados.
"""

import firebirdsql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import FIREBIRD_USER, FIREBIRD_PASSWORD


def limpar_duplicados_gdb(caminho_gdb=""):
    """
    Remove duplicatas da tabela CADCNS no Firebird.
    
    Parâmetros:
        caminho_gdb: caminho do arquivo .GDB do Firebird
    
    Estratégia:
    1. Pego TODOS os pacientes com CNS preenchido
    2. Agrupo por CNS
    3. Pra cada grupo com mais de 1:
       - Ordeno por pontuação decrescente
       - A primeira fica (melhor pontuada)
       - As demais são deletadas
    
    Retorna relatório: grupos com duplicidade e registros removidos.
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

        # --- PASSO 1: CARREGAR TODOS OS PACIENTES ---
        query = """
            SELECT RDB$DB_KEY, CNS, NUM_CPF, LOGPCN, TEL_PCNTE
            FROM CADCNS
            WHERE CNS IS NOT NULL
        """
        cursor.execute(query)
        pacientes = cursor.fetchall()

        # --- PASSO 2: AGRUPAR POR SUS ---
        agrupados_por_sus = {}
        for p in pacientes:
            db_key = p[0]
            sus_limpo = str(p[1]).strip() if p[1] else ""
            if not sus_limpo:
                continue

            ficha = {
                'db_key': db_key,
                'sus': sus_limpo,
                'cpf': str(p[2]).strip() if p[2] else "",
                'endereco': str(p[3]).strip() if p[3] else "",
                'tel': str(p[4]).strip() if p[4] else ""
            }
            if sus_limpo not in agrupados_por_sus:
                agrupados_por_sus[sus_limpo] = []
            agrupados_por_sus[sus_limpo].append(ficha)

        # --- PASSO 3: AVALIAR E ESCOLHER A MELHOR FICHA ---
        ids_para_deletar = []
        pacientes_arrumados = 0

        for sus, lista_fichas in agrupados_por_sus.items():
            if len(lista_fichas) > 1:
                pacientes_arrumados += 1

                # Função de pontuação DEFINIDA DENTRO do loop
                # pra ter acesso ao escopo local
                def calcular_pontuacao(ficha):
                    pontos = 0
                    # CPF é o campo mais importante (5 pontos)
                    if ficha['cpf'] and len(ficha['cpf']) >= 11:
                        pontos += 5
                    # Endereço e telefone: 1 ponto cada
                    if ficha['endereco']:
                        pontos += 1
                    if ficha['tel']:
                        pontos += 1
                    return pontos

                # Ordeno da MAIOR pra MENOR pontuação
                lista_ordenada = sorted(
                    lista_fichas, key=calcular_pontuacao, reverse=True
                )

                # A primeira (índice 0) é a melhor — mantenho
                # O resto (índice 1+) vão pro deletion
                for ficha_perdedora in lista_ordenada[1:]:
                    ids_para_deletar.append(ficha_perdedora['db_key'])

        # --- PASSO 4: DELETAR AS DUPLICATAS ---
        if ids_para_deletar:
            for db_key in ids_para_deletar:
                cursor.execute(
                    "DELETE FROM CADCNS WHERE RDB$DB_KEY = ?",
                    (db_key,)
                )
            conexao.commit()

            return (
                f"Faxina Concluida!\n"
                f"Pacientes com duplicidade: {pacientes_arrumados}\n"
                f"Cadastros removidos: {len(ids_para_deletar)}"
            )
        else:
            return "Nenhum SUS duplicado foi encontrado."

    except Exception as e:
        return f"Erro na execucao: {e}"

    finally:
        if 'conexao' in locals():
            conexao.close()


if __name__ == "__main__":
    gdb = input("Caminho do .gdb: ").strip()
    print(limpar_duplicados_gdb(gdb))
