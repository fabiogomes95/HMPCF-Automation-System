# ==============================================================================
# 👻 CAÇA-FANTASMAS: REMOVEDOR DE DUPLICATAS (BPA)
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

        # Mostra quantos pacientes têm o mesmo nome repetido
        cur.execute("""
            SELECT NOME, COUNT(*) 
            FROM CADCNS 
            GROUP BY NOME 
            HAVING COUNT(*) > 1 
            ORDER BY COUNT(*) DESC
        """)
        repetidos = cur.fetchall()

        if not repetidos:
            print("✅ Tudo certo! Nenhuma duplicata encontrada no banco.")
            con.close()
            return

        print("\n⚠️ ATENÇÃO! Encontrei os seguintes registros clonados no banco:")
        for nome, qtd in repetidos:
            nome_exibicao = nome if nome else "[CADASTRO EM BRANCO / FANTASMA]"
            print(f" -> {qtd} repetições: {nome_exibicao}")

        escolha = input("\nQuer que eu apague os clones e deixe apenas UMA cópia de cada? (S/N): ")

        if escolha.upper() == 'S':
            print("\n⏳ Apagando clones... (Isso pode levar alguns segundos)")
            
            # Deleta os repetidos e mantém apenas o registro mais atual
            cur.execute("""
                DELETE FROM CADCNS A
                WHERE EXISTS (
                    SELECT 1 FROM CADCNS B
                    WHERE COALESCE(B.NOME, '') = COALESCE(A.NOME, '')
                    AND COALESCE(B.DTNASC, '') = COALESCE(A.DTNASC, '')
                    AND B.RDB$DB_KEY > A.RDB$DB_KEY
                )
            """)
            
            con.commit()
            print("✅ Limpeza cirúrgica concluída! Todos os clones e fantasmas foram removidos.")
        else:
            print("❌ Operação cancelada.")

        con.close()

    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    iniciar_limpeza()