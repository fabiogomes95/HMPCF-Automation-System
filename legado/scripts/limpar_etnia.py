# ==============================================================================
# SCRIPT: LIMPAR_ETNIA.PY — Corrige campo ETNIA no Firebird (BPAMAG.GDB)
# ==============================================================================
# Problema: Alguns registros têm ETNIA = '000', '0000', '00' etc.
# Solução: Substitui esses valores por '' (vazio), que é o correto quando
#          a etnia não foi informada.
# ==============================================================================

import firebirdsql
import re

CAMINHO_GDB = r'C:/BPA/BPAMAG.GDB'
USER = 'SYSDBA'
PASS = 'masterkey'


def apenas_zeros(valor: str) -> bool:
    """Retorna True se o valor for composto apenas por zeros (ex: '0', '00', '000')."""
    limpo = valor.strip()
    return bool(limpo) and re.fullmatch(r'0+', limpo) is not None


def limpar_etnia():
    try:
        print(f"Conectando ao banco em: {CAMINHO_GDB}")
        con = firebirdsql.connect(
            host='localhost',
            database=CAMINHO_GDB,
            user=USER,
            password=PASS,
            charset='WIN1252',
        )
        cur = con.cursor()

        # --- DIAGNÓSTICO: quais etnias existem hoje ---
        print("\nLevantando valores atuais do campo ETNIA...")
        cur.execute("SELECT ETNIA, COUNT(*) FROM CADCNS GROUP BY ETNIA")
        grupos = cur.fetchall()

        registros_para_limpar = []
        print("\n{:<12} {:>10}".format("ETNIA", "QTD"))
        print("-" * 24)
        for etnia, qtd in sorted(grupos, key=lambda x: (x[0] or '')):
            etnia_val = etnia if etnia is not None else "(NULL)"
            print("{:<12} {:>10}".format(repr(etnia_val), qtd))
            if etnia is not None and apenas_zeros(etnia):
                registros_para_limpar.append((etnia, qtd))

        if not registros_para_limpar:
            print("\nNenhuma ETNIA com valor '000' (ou variação) encontrada. Banco já está correto.")
            con.close()
            return

        total = sum(q for _, q in registros_para_limpar)
        print("\n" + "=" * 50)
        print("PROBLEMA ENCONTRADO")
        print("=" * 50)
        for etnia, qtd in registros_para_limpar:
            print(f"  ETNIA = {repr(etnia)}  ->  {qtd} registro(s)")
        print(f"\nTotal a corrigir: {total} registro(s)")
        print("Acao: serao substituidos por '' (string vazia)")
        print("=" * 50)

        escolha = input("\nDeseja aplicar a correcao agora? (S/N): ")
        if escolha.strip().upper() != 'S':
            print("\nOperacao cancelada. Nenhuma alteracao foi feita.")
            con.close()
            return

        print("\nAplicando correcao...")
        for etnia, _ in registros_para_limpar:
            cur.execute(
                "UPDATE CADCNS SET ETNIA = '' WHERE ETNIA = ?",
                (etnia,),
            )
            print(f"  ETNIA = {repr(etnia)}  ->  {cur.rowcount} registro(s) corrigido(s)")

        con.commit()
        print("\nCorrecao concluida com sucesso! Banco pronto para exportacao BPA.")
        con.close()

    except Exception as e:
        print(f"\nERRO: {e}")


if __name__ == "__main__":
    limpar_etnia()
