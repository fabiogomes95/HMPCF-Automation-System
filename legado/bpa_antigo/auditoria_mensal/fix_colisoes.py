"""Corrige colisoes de (PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ) em S_PRD.

Para cada slot colidido, mantem a linha com o menor RDB$DB_KEY (mais antiga)
no lugar, e realoca as demais para o proximo slot livre daquele profissional
na competencia (continuando apos o maior folha/seq ja usado por ele, regra
de 99 por folha -- igual bpa_gerador.calcular_atendimentos_producao).

So mexe em PRD_FLH/PRD_SEQ. Nao toca em paciente/procedimento/data/CBO.

Uso:
    python fix_colisoes.py             # dry-run, so mostra o plano
    python fix_colisoes.py --aplicar   # grava de verdade (faca backup antes)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + r"\..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + r"\..")
import bpa_gerador as bpa


def main(aplicar: bool):
    con = bpa.conectar()
    cur = con.cursor()

    cur.execute("""
        SELECT PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ, COUNT(*)
        FROM S_PRD
        GROUP BY PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ
        HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"{len(grupos)} slots colididos.")

    # maior (folha,seq) atual por profissional/competencia -> indice linear
    def idx(folha, seq):
        return (int(folha) - 1) * 99 + int(seq)

    max_idx = {}  # (cnsmed, mvm) -> indice linear maximo em uso
    cur.execute("SELECT PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ FROM S_PRD")
    for cnsmed, mvm, flh, seq in cur.fetchall():
        try:
            i = idx(flh, seq)
        except (ValueError, TypeError):
            continue
        chave = (cnsmed, mvm)
        if chave not in max_idx or i > max_idx[chave]:
            max_idx[chave] = i

    # Plano: para cada grupo colidido, N-1 linhas precisam ser realocadas
    # (a que sobra no slot original nao e tocada). RDB$DB_KEY nao pode ser
    # trazido pro Python (o driver quebra decodificando como texto), entao
    # a escolha "qual linha mover" e feita 100% no servidor via subquery
    # correlacionada (FIRST 1 ... WHERE ainda esta no slot antigo).
    plano = []  # (cnsmed, mvm, flh_antiga, seq_antiga, novo_folha, novo_seq)
    for cnsmed, mvm, flh, seq, qtd in grupos:
        chave = (cnsmed, mvm)
        for _ in range(qtd - 1):
            max_idx[chave] = max_idx.get(chave, idx(flh, seq)) + 1
            novo_i = max_idx[chave]
            novo_folha = (novo_i - 1) // 99 + 1
            novo_seq = (novo_i - 1) % 99 + 1
            plano.append((cnsmed, mvm, flh, seq, novo_folha, novo_seq))

    print(f"{len(plano)} linhas serao realocadas.\n")
    for p in plano[:30]:
        print(f"  cnsmed={p[0]} slot antigo={p[2]}/{p[3]} -> novo slot={p[4]:03d}/{p[5]:02d}")
    if len(plano) > 30:
        print(f"  ... e mais {len(plano) - 30} linhas")

    if not aplicar:
        print("\n(dry-run -- nada foi gravado. rode com --aplicar para gravar)")
        con.close()
        return

    # firebirdsql (driver python) da erro de parser em RDB$DB_KEY dentro de
    # subquery parametrizada -- gera um script e roda via isql (que ja usa
    # RDB$DB_KEY sem problema em dedup.sql deste mesmo projeto). Usa alias
    # de tabela (X/Y) -- sem alias o isql tambem falha com "Column unknown".
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_apply_colisoes.sql")
    with open(sql_path, "w", encoding="ascii") as f:
        for cnsmed, mvm, flh, seq, novo_folha, novo_seq in plano:
            f.write(
                f"UPDATE S_PRD X SET X.PRD_FLH = '{str(novo_folha).zfill(3)}', X.PRD_SEQ = '{str(novo_seq).zfill(2)}' "
                f"WHERE X.RDB$DB_KEY = (SELECT FIRST 1 Y.RDB$DB_KEY FROM S_PRD Y "
                f"WHERE Y.PRD_CNSMED = '{cnsmed}' AND Y.PRD_MVM = '{mvm}' AND Y.PRD_FLH = '{flh}' AND Y.PRD_SEQ = '{seq}');\n"
            )
        f.write("COMMIT;\nQUIT;\n")

    con.close()

    import subprocess
    r = subprocess.run(
        [r"C:\Firebird_1_5\bin\isql.exe", "-u", bpa.FIREBIRD_USER, "-p", bpa.FIREBIRD_PASSWORD,
         bpa.FIREBIRD_PATH, "-i", sql_path],
        capture_output=True, text=True,
    )
    print(r.stdout)
    print(r.stderr)
    os.remove(sql_path)
    if r.returncode != 0:
        print("ERRO ao aplicar via isql -- verifique o que foi commitado ate a falha.")
        return
    print(f"{len(plano)} linhas atualizadas via isql.")

    # confere que nao sobrou colisao (conexao nova -- a anterior foi fechada)
    con2 = bpa.conectar()
    cur2 = con2.cursor()
    cur2.execute("""
        SELECT PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ, COUNT(*)
        FROM S_PRD
        GROUP BY PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ
        HAVING COUNT(*) > 1
    """)
    restantes = cur2.fetchall()
    print(f"Colisoes restantes apos o fix: {len(restantes)}")
    con2.close()


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
