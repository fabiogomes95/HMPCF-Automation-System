# ==============================================================================
# 👻 CAÇA-FANTASMAS: REMOVEDOR DE DUPLICATAS (SEM UDF / SEM TRIM)
# ==============================================================================

import firebirdsql

CAMINHO_GDB = r'C:/BPA/BPAMAG.GDB'
USER = 'SYSDBA'
PASS = 'masterkey'

def iniciar_limpeza():
    try:
        print(f"🔍 Conectando ao banco em: {CAMINHO_GDB}")
        con = firebirdsql.connect(host='localhost', database=CAMINHO_GDB, user=USER, password=PASS, charset='WIN1252')
        cur = con.cursor()

        # Mostra quantos pacientes têm o mesmo NOME + CNS repetidos
        # Trocamos o TRIM por verificações diretas de nulo e vazio
        cur.execute("""
            SELECT NOME, CNS, COUNT(*) 
            FROM CADCNS 
            WHERE CNS IS NOT NULL AND CNS <> '' AND CNS <> '               '
            GROUP BY NOME, CNS 
            HAVING COUNT(*) > 1 
            ORDER BY COUNT(*) DESC
        """)
        repetidos = cur.fetchall()

        if not repetidos:
            print("✅ Tudo certo! Nenhuma duplicata exata encontrada no banco.")
            con.close()
            return

        print("\n⚠️ ATENÇÃO! Encontrei os seguintes registros clonados (Nome + Documento):")
        for nome, cns, qtd in repetidos:
            nome_exibicao = nome if nome else "[NOME EM BRANCO]"
            cns_exibicao = cns if cns else "[SEM SUS]"
            print(f" -> {qtd} repetições: {nome_exibicao} (SUS: {cns_exibicao})")

        escolha = input("\nQuer que eu apague os clones e deixe apenas UMA cópia de cada? (S/N): ")

        if escolha.upper() == 'S':
            print("\n⏳ Apagando clones... (Isso pode levar alguns segundos)")
            
            # Deleta os repetidos sem usar COALESCE ou TRIM
            # Comparamos diretamente os campos e tratamos os vazios com IS NOT NULL
            cur.execute("""
                DELETE FROM CADCNS A
                WHERE EXISTS (
                    SELECT 1 FROM CADCNS B
                    WHERE B.NOME = A.NOME
                    AND B.DTNASC = A.DTNASC
                    AND (
                        (B.CNS = A.CNS AND A.CNS IS NOT NULL AND A.CNS <> '' AND A.CNS <> '               ')
                        OR 
                        (B.NUM_CPF = A.NUM_CPF AND A.NUM_CPF IS NOT NULL AND A.NUM_CPF <> '' AND A.NUM_CPF <> '           ')
                    )
                    AND B.RDB$DB_KEY > A.RDB$DB_KEY
                )
            """)
            
            con.commit()
            print("✅ Limpeza cirúrgica concluída! Todos os clones foram removidos com segurança.")
        else:
            print("❌ Operação cancelada.")

        con.close()

    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    iniciar_limpeza()