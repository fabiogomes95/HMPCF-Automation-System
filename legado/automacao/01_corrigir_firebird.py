"""
CORRECAO_FIREBIRD.py — Dedup automatico no Firebird (BPAMAG.GDB)
=================================================================
1. Agrupa CADCNS por NOME+DTNASC → mescla em 1 registro
2. Agrupa por NUM_CPF → mescla em 1 registro
3. Agrupa por CNS → mescla em 1 registro
4. Atualiza referencias nas tabelas relacionadas (S_PA, S_PAPA, etc.)

Uso: python automacao/01_corrigir_firebird.py
"""

import firebirdsql
import re
import os

FB = dict(
    host='localhost',
    database=r'C:\BPA\BPAMAG.GDB',
    user='SYSDBA',
    password='masterkey',
    charset='WIN1252'
)

LIMPAR_NUM = re.compile(r'\D')


def limpar_numero(valor):
    return LIMPAR_NUM.sub('', str(valor)) if valor else ''


def campos_preenchidos(row):
    return sum(1 for v in row if v is not None and str(v).strip())


def merge_group_fb(rowids, cursor, grupo_nome):
    """
    Recebe lista de ID_CADCNS que representam a mesma pessoa.
    Mantem o registro com mais dados, atualiza referencias, deleta os outros.
    Retorna (mantidos, deletados).
    """
    if len(rowids) < 2:
        return 0, 0

    # Firebird limita IN a ~1500 valores — busca em lotes de 1000
    BATCH = 1000
    rows = []
    for i in range(0, len(rowids), BATCH):
        batch = rowids[i:i + BATCH]
        placeholders = ','.join('?' for _ in batch)
        cursor.execute(f"""
            SELECT ID_CADCNS, CNS, NUM_CPF, NOME, DTNASC, SEXO, RACA, MAEPCN,
                   LOGPCN, NUMPCN, BAIRRO_PCNTE, CEPPCN, IBGE, ETNIA,
                   NACIONALIDADE, DDTEL_PCNTE, TEL_PCNTE, CO_LOGRAD
            FROM CADCNS WHERE ID_CADCNS IN ({placeholders})
        """, batch)
        rows.extend(cursor.fetchall())
    cols = [desc[0] for desc in cursor.description]

    # Escolhe o melhor (mais campos preenchidos, menor ID como desempate)
    rows.sort(key=lambda r: (-campos_preenchidos(r[1:]), r[0]))
    manter = rows[0]
    manter_id = manter[0]
    manter_dict = dict(zip(cols, manter))

    # Acumula todos os campos para update unico no final
    updates = {}
    novos_cns = None
    novos_cpf = None
    cns_m = limpar_numero(manter_dict.get('CNS'))
    cpf_m = limpar_numero(manter_dict.get('NUM_CPF'))

    for r in rows[1:]:
        r_dict = dict(zip(cols, r))

        # Copia campos vazios do mantido que existem no secundario
        for col in cols[1:]:
            if col in ('CNS', 'NUM_CPF'):
                continue
            db_val = manter_dict.get(col)
            if (db_val is None or str(db_val).strip() == '') and r_dict.get(col):
                updates[col] = r_dict[col]

        # CNS: prefere 15 digitos
        cns_r = limpar_numero(r_dict.get('CNS'))
        if cns_r and (not cns_m or len(cns_m) != 15) and len(cns_r) == 15:
            cns_m = cns_r
            updates['CNS'] = cns_r

        # CPF: prefere 11 digitos
        cpf_r = limpar_numero(r_dict.get('NUM_CPF'))
        if cpf_r and (not cpf_m or len(cpf_m) != 11) and len(cpf_r) == 11:
            cpf_m = cpf_r
            updates['NUM_CPF'] = cpf_r

    # Aplica todos os updates de uma vez
    if updates:
        set_clause = ', '.join(f"{col} = ?" for col in updates)
        cursor.execute(
            f"UPDATE CADCNS SET {set_clause} WHERE ID_CADCNS = ?",
            list(updates.values()) + [manter_id]
        )

    # Deleta duplicatas e atualiza referencias
    def safe_update(tabela, coluna, valor_novo, valor_velho):
        if not valor_velho or not valor_novo or valor_velho == valor_novo:
            return
        try:
            cursor.execute(
                f"UPDATE {tabela} SET {coluna} = ? WHERE {coluna} = ?",
                (valor_novo, valor_velho)
            )
        except Exception:
            pass

    cns_final = (manter_dict.get('CNS') or '').strip()
    cpf_final = (manter_dict.get('NUM_CPF') or '').strip()
    deletados = 0
    for r in rows[1:]:
        r_id = r[0]
        r_dict = dict(zip(cols, r))
        cns_old = (r_dict.get('CNS') or '').strip()
        cpf_old = (r_dict.get('NUM_CPF') or '').strip()
        if cns_old and cns_final:
            safe_update('S_PA', 'PA_CNSPCN', cns_final, cns_old)
            safe_update('S_CDN', 'CDN_CNS', cns_final, cns_old)
        if cpf_old and cpf_final:
            safe_update('S_PASRV', 'PASRV_CPF', cpf_final, cpf_old)
        cursor.execute("DELETE FROM CADCNS WHERE ID_CADCNS = ?", (r_id,))
        deletados += 1

    return 1, deletados


def main():
    con = firebirdsql.connect(**FB)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM CADCNS")
    total_inicial = cur.fetchone()[0]
    print(f"Total CADCNS antes: {total_inicial}\n")

    total_removidos = 0
    total_mantidos = 0

    # ===================================================================
    # FASE 0: Validar CPF/CNS com algoritmos oficiais matematicos
    # ===================================================================
    print("=" * 60)
    print("FASE 0: Validando CPF/CNS (algoritmo oficial)...")
    print("=" * 60)

    def valida_cpf(cpf):
        if not cpf or len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        try:
            soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
            digito_1 = (soma_1 * 10 % 11) % 10
            soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
            digito_2 = (soma_2 * 10 % 11) % 10
            return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]
        except (ValueError, IndexError):
            return False

    def valida_cns(cns):
        if not cns or len(cns) != 15 or cns[0] not in '12789':
            return False
        try:
            if cns[0] in '789':
                return sum(int(cns[i]) * (15 - i) for i in range(15)) % 11 == 0
            pis = cns[:11]
            soma = sum(int(pis[i]) * (15 - i) for i in range(11))
            resto = soma % 11
            dv = 11 - resto
            if dv == 11:
                dv = 0
            if dv == 10:
                soma += 2
                resto = soma % 11
                dv = 11 - resto
                resultado = pis + "001" + str(dv)
            else:
                resultado = pis + "000" + str(dv)
            return cns == resultado
        except (ValueError, IndexError):
            return False

    cur.execute("SELECT ID_CADCNS, CNS, NUM_CPF, NOME FROM CADCNS")
    limpos_cpf = limpos_cns = deletados_sem_doc = 0
    for r in cur.fetchall():
        cns = (r[1] or '').strip()
        cpf = (r[2] or '').strip()
        cns_clean = limpar_numero(cns)
        cpf_clean = limpar_numero(cpf)
        cpf_valido = valida_cpf(cpf_clean) if cpf_clean else False
        cns_valido = valida_cns(cns_clean) if cns_clean else False

        if cpf and not cpf_valido:
            cur.execute("UPDATE CADCNS SET NUM_CPF = '' WHERE ID_CADCNS = ?", (r[0],))
            limpos_cpf += 1
        if cns and not cns_valido:
            cur.execute("UPDATE CADCNS SET CNS = '' WHERE ID_CADCNS = ?", (r[0],))
            limpos_cns += 1
        if not cpf_valido and not cns_valido:
            deletados_sem_doc += 1
            cur.execute("DELETE FROM CADCNS WHERE ID_CADCNS = ?", (r[0],))

    con.commit()
    total_removidos += deletados_sem_doc
    print(f"  CPF invalidos limpos (algoritmo oficial):   {limpos_cpf}")
    print(f"  CNS invalidos limpos (algoritmo oficial):   {limpos_cns}")
    print(f"  Registros deletados (sem doc valido):       {deletados_sem_doc}")
    print(f"  (CPF/CNS com digito verificador errado)\n")

    # ===================================================================
    # FASE 1: Duplicatas por NOME + DTNASC
    # ===================================================================
    print("=" * 60)
    print("FASE 1: Agrupando CADCNS por NOME + DTNASC...")
    print("=" * 60)

    cur.execute("""
        SELECT NOME, DTNASC, COUNT(*) as cnt
        FROM CADCNS
        WHERE NOME IS NOT NULL AND NOME != ''
          AND DTNASC IS NOT NULL AND DTNASC != ''
        GROUP BY NOME, DTNASC
        HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"  Grupos com mesmo NOME+DTNASC: {len(grupos)}")

    mantido = deletados = 0
    for g in grupos:
        cur.execute("SELECT ID_CADCNS FROM CADCNS WHERE NOME = ? AND DTNASC = ? ORDER BY ID_CADCNS", (g[0], g[1]))
        rowids = [r[0] for r in cur.fetchall()]
        m, d = merge_group_fb(rowids, cur, 'NOME+DTNASC')
        mantido += m
        deletados += d

    con.commit()
    total_mantidos += mantido
    total_removidos += deletados
    print(f"  Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ===================================================================
    # FASE 2: Duplicatas por CPF
    # ===================================================================
    print("=" * 60)
    print("FASE 2: Agrupando CADCNS por NUM_CPF...")
    print("=" * 60)

    cur.execute("""
        SELECT NUM_CPF, COUNT(*) as cnt
        FROM CADCNS
        WHERE NUM_CPF IS NOT NULL AND NUM_CPF != ''
        GROUP BY NUM_CPF
        HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"  Grupos com mesmo CPF: {len(grupos)}")

    mantido = deletados = 0
    for g in grupos:
        cur.execute("SELECT ID_CADCNS FROM CADCNS WHERE NUM_CPF = ? ORDER BY ID_CADCNS", (g[0],))
        rowids = [r[0] for r in cur.fetchall()]
        m, d = merge_group_fb(rowids, cur, 'CPF')
        mantido += m
        deletados += d

    con.commit()
    total_mantidos += mantido
    total_removidos += deletados
    print(f"  Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ===================================================================
    # FASE 3: Duplicatas por CNS
    # ===================================================================
    print("=" * 60)
    print("FASE 3: Agrupando CADCNS por CNS...")
    print("=" * 60)

    cur.execute("""
        SELECT CNS, COUNT(*) as cnt
        FROM CADCNS
        WHERE CNS IS NOT NULL AND CNS != ''
        GROUP BY CNS
        HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"  Grupos com mesmo CNS: {len(grupos)}")

    mantido = deletados = 0
    for g in grupos:
        cur.execute("SELECT ID_CADCNS FROM CADCNS WHERE CNS = ? ORDER BY ID_CADCNS", (g[0],))
        rowids = [r[0] for r in cur.fetchall()]
        m, d = merge_group_fb(rowids, cur, 'CNS')
        mantido += m
        deletados += d

    con.commit()
    total_mantidos += mantido
    total_removidos += deletados
    print(f"  Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ===================================================================
    # RESUMO FINAL
    # ===================================================================
    cur.execute("SELECT COUNT(*) FROM CADCNS")
    total_final = cur.fetchone()[0]

    print("=" * 60)
    print("  RESUMO DA CORRECAO (FIREBIRD)")
    print("=" * 60)
    print(f"  CADCNS antes:             {total_inicial}")
    print(f"  Registros removidos:      {total_removidos}")
    print(f"  Registros mantidos:       {total_mantidos}")
    print(f"  CADCNS depois:            {total_final}")
    print(f"  Diferenca:                {total_inicial - total_final}")
    print("=" * 60)

    # Verifica se ainda restam duplicatas (sem subquery — Firebird antigo)
    cur.execute("""
        SELECT NUM_CPF, COUNT(*) as cnt
        FROM CADCNS
        WHERE NUM_CPF IS NOT NULL AND NUM_CPF != ''
        GROUP BY NUM_CPF
        HAVING COUNT(*) > 1
    """)
    restam_cpf = len(cur.fetchall())
    cur.execute("""
        SELECT CNS, COUNT(*) as cnt
        FROM CADCNS
        WHERE CNS IS NOT NULL AND CNS != ''
        GROUP BY CNS
        HAVING COUNT(*) > 1
    """)
    restam_cns = len(cur.fetchall())
    cur.execute("""
        SELECT NOME, DTNASC, COUNT(*) as cnt
        FROM CADCNS
        WHERE NOME IS NOT NULL AND NOME != ''
          AND DTNASC IS NOT NULL AND DTNASC != ''
        GROUP BY NOME, DTNASC
        HAVING COUNT(*) > 1
    """)
    restam_nome = len(cur.fetchall())

    if restam_cpf or restam_cns or restam_nome:
        print(f"\n  ATENCAO: ainda restam duplicatas!")
        print(f"    Por CPF: {restam_cpf}")
        print(f"    Por CNS: {restam_cns}")
        print(f"    Por NOME+DT: {restam_nome}")
    else:
        print("\n  Nenhuma duplicata restante. CADCNS limpo!")

    con.close()
    print()


if __name__ == '__main__':
    main()
