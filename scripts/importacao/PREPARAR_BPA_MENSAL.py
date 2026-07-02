"""
PREPARAR_BPA_MENSAL.py — Pipeline mensal: PostgreSQL -> Firebird (CADCNS)
==========================================================================
Execute este script no inicio de cada mes antes de digitar o BPA.

O que ele faz (em ordem):
  ETAPA 1 — Migra pacientes novos do PostgreSQL para o Firebird CADCNS
             (apenas insere quem ainda nao existe — dedup por CNS/CPF)
  ETAPA 2 — Deduplica e corrige o Firebird CADCNS:
             Fase 0: remove CPF/CNS matematicamente invalidos
             Fase 1: mescla duplicatas por NOME + DATA NASCIMENTO
             Fase 2: mescla duplicatas por CPF
             Fase 3: mescla duplicatas por CNS
             (atualiza referencias em S_PA, S_CDN, S_PASRV)

Uso:
    python automacao/PREPARAR_BPA_MENSAL.py

Configuracao (.env em legado/ ou scripts/):
    POSTGRES_HOST      (padrao: localhost)
    POSTGRES_PORT      (padrao: 5432)
    POSTGRES_DB        (padrao: hmpcf)
    POSTGRES_USER      (padrao: postgres)
    POSTGRES_PASSWORD  (obrigatorio)
    FIREBIRD_USER      (padrao: SYSDBA)
    FIREBIRD_PASSWORD  (padrao: masterkey)
"""

import os
import re
import sys

import firebirdsql

try:
    import psycopg2
except ImportError:
    print("ERRO: psycopg2 nao instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    for _p in [
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', '.env'),
    ]:
        if os.path.exists(os.path.normpath(_p)):
            load_dotenv(os.path.normpath(_p))
            break
except ImportError:
    pass

# ── CONFIGURACOES ─────────────────────────────────────────────────────────────

POSTGRES_CONFIG = dict(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', '5432')),
    dbname=os.getenv('POSTGRES_DB', 'hmpcf'),
    user=os.getenv('POSTGRES_USER', 'postgres'),
    password=os.getenv('POSTGRES_PASSWORD', ''),
)

FIREBIRD_CONFIG = dict(
    host='localhost',
    database=r'C:\BPA\BPAMAG.GDB',
    user=os.getenv('FIREBIRD_USER', 'SYSDBA'),
    password=os.getenv('FIREBIRD_PASSWORD', 'masterkey'),
    charset='WIN1252',
)

LOTE = 50

COLUNAS_FB_INSERT = [
    'ID_CADCNS',
    'CNS', 'NUM_CPF', 'NOME', 'DTNASC', 'SEXO', 'RACA', 'MAEPCN',
    'LOGPCN', 'NUMPCN', 'BAIRRO_PCNTE', 'CEPPCN', 'IBGE',
    'CO_LOGRAD',
    'ETNIA', 'NACIONALIDADE',
    'DDTEL_PCNTE', 'TEL_PCNTE',
]

# ── FUNCOES AUXILIARES ────────────────────────────────────────────────────────

LIMPAR_NUM = re.compile(r'\D')

def limpar_numero(valor):
    return LIMPAR_NUM.sub('', str(valor)) if valor else ''

def mascarar_doc(valor):
    """Mascara CNS/CPF em logs — mantem so os 4 ultimos digitos."""
    s = str(valor) if valor else ''
    return ('*' * max(0, len(s) - 4)) + s[-4:] if s else '(vazio)'

def validar_texto(valor, max_len=9999):
    if valor is None:
        return ''
    s = str(valor).strip().upper()
    return s[:max_len] if len(s) > max_len else s

def validar_sexo(valor):
    if not valor:
        return 'I'
    s = str(valor).strip().upper()
    return s if s in ('M', 'F') else 'I'

def validar_dtnasc(valor):
    if not valor:
        return None
    v = str(valor).strip().replace('-', '').replace('/', '')
    return v if len(v) == 8 and v.isdigit() else None

def valida_cpf(cpf):
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    try:
        d1 = (sum(int(cpf[i]) * (10 - i) for i in range(9)) * 10 % 11) % 10
        d2 = (sum(int(cpf[i]) * (11 - i) for i in range(10)) * 10 % 11) % 10
        return str(d1) == cpf[9] and str(d2) == cpf[10]
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

def campos_preenchidos(row):
    return sum(1 for v in row if v is not None and str(v).strip())

def paciente_existe_fb(fb_cur, cns, cpf):
    if cns:
        fb_cur.execute("SELECT 1 FROM CADCNS WHERE CNS = ?", (cns,))
        if fb_cur.fetchone():
            return True
    if cpf:
        fb_cur.execute("SELECT 1 FROM CADCNS WHERE NUM_CPF = ?", (cpf,))
        if fb_cur.fetchone():
            return True
    return False

def merge_group_fb(rowids, cursor):
    """Mescla grupo de duplicatas no Firebird: mantém o com mais dados, deleta os outros."""
    if len(rowids) < 2:
        return 0, 0

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

    rows.sort(key=lambda r: (-campos_preenchidos(r[1:]), r[0]))
    manter = rows[0]
    manter_id = manter[0]
    manter_dict = dict(zip(cols, manter))

    updates = {}
    cns_m = limpar_numero(manter_dict.get('CNS'))
    cpf_m = limpar_numero(manter_dict.get('NUM_CPF'))

    for r in rows[1:]:
        r_dict = dict(zip(cols, r))
        for col in cols[1:]:
            if col in ('CNS', 'NUM_CPF'):
                continue
            db_val = manter_dict.get(col)
            if (db_val is None or str(db_val).strip() == '') and r_dict.get(col):
                updates[col] = r_dict[col]
        cns_r = limpar_numero(r_dict.get('CNS'))
        if cns_r and (not cns_m or len(cns_m) != 15) and len(cns_r) == 15:
            cns_m = cns_r
            updates['CNS'] = cns_r
        cpf_r = limpar_numero(r_dict.get('NUM_CPF'))
        if cpf_r and (not cpf_m or len(cpf_m) != 11) and len(cpf_r) == 11:
            cpf_m = cpf_r
            updates['NUM_CPF'] = cpf_r

    if updates:
        set_clause = ', '.join(f"{col} = ?" for col in updates)
        cursor.execute(
            f"UPDATE CADCNS SET {set_clause} WHERE ID_CADCNS = ?",
            list(updates.values()) + [manter_id]
        )

    def safe_update(tabela, coluna, novo, velho):
        if not velho or not novo or velho == novo:
            return
        try:
            cursor.execute(f"UPDATE {tabela} SET {coluna} = ? WHERE {coluna} = ?", (novo, velho))
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
            safe_update('S_PA',   'PA_CNSPCN', cns_final, cns_old)
            safe_update('S_CDN',  'CDN_CNS',   cns_final, cns_old)
        if cpf_old and cpf_final:
            safe_update('S_PASRV', 'PASRV_CPF', cpf_final, cpf_old)
        cursor.execute("DELETE FROM CADCNS WHERE ID_CADCNS = ?", (r_id,))
        deletados += 1

    return 1, deletados


# ══════════════════════════════════════════════════════════════════════════════
#  ETAPA 1 — PostgreSQL -> Firebird
# ══════════════════════════════════════════════════════════════════════════════

def etapa_migracao(pg_con, fb_con):
    print("=" * 60)
    print("  ETAPA 1: Migracao PostgreSQL -> Firebird (CADCNS)")
    print("=" * 60)

    pg_cur = pg_con.cursor()
    fb_cur = fb_con.cursor()

    pg_cur.execute("SELECT COUNT(*) FROM pacientes")
    total_pg = pg_cur.fetchone()[0]
    print(f"  Pacientes no PostgreSQL: {total_pg}")

    fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
    max_id = fb_cur.fetchone()[0]
    novo_id = max_id if max_id is not None else 0
    print(f"  Maior ID_CADCNS no Firebird: {max_id}  |  Proximo: {novo_id + 1}\n")

    pg_cur.execute("""
        SELECT cns, num_cpf, nome, dtnasc, sexo, raca, maepcn,
               logpcn, numpcn, bairro_pcnte, ceppcn, ibge,
               nacionalidade, ddtel_pcnte, tel_pcnte
        FROM pacientes ORDER BY id
    """)
    rows = pg_cur.fetchall()

    placeholders = ', '.join(['?'] * len(COLUNAS_FB_INSERT))
    cols = ', '.join(COLUNAS_FB_INSERT)
    sql_insert = f"INSERT INTO CADCNS ({cols}) VALUES ({placeholders})"

    inseridos = duplicatas = sem_doc = sem_nome = erros = processados = 0

    for row in rows:
        cns_raw, cpf_raw, nome_raw, dn_raw, sexo_raw, raca_raw, mae_raw, \
            log_raw, num_raw, bairro_raw, cep_raw, ibge_raw, \
            nac_raw, ddd_raw, tel_raw = row

        cns = limpar_numero(cns_raw)
        cpf = limpar_numero(cpf_raw)

        if not cns and not cpf:
            sem_doc += 1
            continue

        nome = validar_texto(nome_raw, 30)
        if not nome:
            sem_nome += 1
            continue

        try:
            if paciente_existe_fb(fb_cur, cns, cpf):
                duplicatas += 1
                processados += 1
                if processados % LOTE == 0:
                    fb_con.commit()
                continue
        except Exception as e:
            fb_con.rollback()
            print(f"  ERRO verificar duplicidade CNS={mascarar_doc(cns)} CPF={mascarar_doc(cpf)}: {e}")
            erros += 1
            continue

        novo_id += 1
        valores = [
            novo_id,
            cns, cpf, nome,
            validar_dtnasc(dn_raw),
            validar_sexo(sexo_raw),
            validar_texto(raca_raw, 2) or '03',
            validar_texto(mae_raw, 30),
            validar_texto(log_raw, 30) or 'PRINCIPAL',
            validar_texto(num_raw, 5) or 'S/N',
            validar_texto(bairro_raw, 30) or 'CENTRO',
            '59575000', '240360', '081',
            '',
            validar_texto(nac_raw, 3),
            validar_texto(ddd_raw, 2),
            validar_texto(tel_raw, 11),
        ]

        try:
            fb_cur.execute(sql_insert, valores)
            inseridos += 1
        except Exception as e:
            fb_con.rollback()
            print(f"  ERRO inserir CNS={mascarar_doc(cns)} CPF={mascarar_doc(cpf)}: {e}")
            erros += 1
            continue

        processados += 1
        if processados % LOTE == 0:
            try:
                fb_con.commit()
                print(f"  [{processados}/{total_pg}] "
                      f"inseridos={inseridos}  duplicatas={duplicatas}  erros={erros}")
            except Exception as e:
                print(f"  ERRO commit lote: {e}")
                fb_con.rollback()

    try:
        fb_con.commit()
    except Exception as e:
        print(f"  ERRO commit final: {e}")

    print(f"\n  Total PostgreSQL:   {total_pg}")
    print(f"  Inseridos:          {inseridos}")
    print(f"  Ja existiam:        {duplicatas}")
    print(f"  Sem CPF/CNS:        {sem_doc}")
    print(f"  Sem nome:           {sem_nome}")
    print(f"  Erros:              {erros}")
    return inseridos


# ══════════════════════════════════════════════════════════════════════════════
#  ETAPA 2 — Deduplicar e corrigir Firebird CADCNS
# ══════════════════════════════════════════════════════════════════════════════

def etapa_deduplicar(fb_con):
    print("\n" + "=" * 60)
    print("  ETAPA 2: Deduplicacao e correcao do Firebird CADCNS")
    print("=" * 60)

    cur = fb_con.cursor()
    cur.execute("SELECT COUNT(*) FROM CADCNS")
    total_inicial = cur.fetchone()[0]
    print(f"  Total CADCNS antes: {total_inicial}\n")

    total_removidos = 0

    # ── Fase 0: Limpa CPF/CNS matematicamente invalidos ──────────────────────
    print("  Fase 0: Validando CPF/CNS (algoritmo oficial)...")
    cur.execute("SELECT ID_CADCNS, CNS, NUM_CPF FROM CADCNS")
    limpos_cpf = limpos_cns = deletados_sem_doc = 0
    for r in cur.fetchall():
        rid, cns, cpf = r[0], (r[1] or '').strip(), (r[2] or '').strip()
        cns_c = limpar_numero(cns)
        cpf_c = limpar_numero(cpf)
        cpf_ok = valida_cpf(cpf_c) if cpf_c else False
        cns_ok = valida_cns(cns_c) if cns_c else False

        if cpf and not cpf_ok:
            cur.execute("UPDATE CADCNS SET NUM_CPF = '' WHERE ID_CADCNS = ?", (rid,))
            limpos_cpf += 1
        if cns and not cns_ok:
            cur.execute("UPDATE CADCNS SET CNS = '' WHERE ID_CADCNS = ?", (rid,))
            limpos_cns += 1
        if not cpf_ok and not cns_ok:
            cur.execute("DELETE FROM CADCNS WHERE ID_CADCNS = ?", (rid,))
            deletados_sem_doc += 1

    fb_con.commit()
    total_removidos += deletados_sem_doc
    print(f"    CPF invalidos limpos:   {limpos_cpf}")
    print(f"    CNS invalidos limpos:   {limpos_cns}")
    print(f"    Deletados (sem doc):    {deletados_sem_doc}\n")

    # ── Fase 1: Duplicatas por NOME + DTNASC ─────────────────────────────────
    print("  Fase 1: Duplicatas por NOME + DTNASC...")
    cur.execute("""
        SELECT NOME, DTNASC, COUNT(*) FROM CADCNS
        WHERE NOME IS NOT NULL AND NOME != ''
          AND DTNASC IS NOT NULL AND DTNASC != ''
        GROUP BY NOME, DTNASC HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"    Grupos encontrados: {len(grupos)}")
    mantido = deletados = 0
    for g in grupos:
        cur.execute("SELECT ID_CADCNS FROM CADCNS WHERE NOME = ? AND DTNASC = ? ORDER BY ID_CADCNS", (g[0], g[1]))
        ids = [r[0] for r in cur.fetchall()]
        m, d = merge_group_fb(ids, cur)
        mantido += m; deletados += d
    fb_con.commit()
    total_removidos += deletados
    print(f"    Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ── Fase 2: Duplicatas por CPF ────────────────────────────────────────────
    print("  Fase 2: Duplicatas por CPF...")
    cur.execute("""
        SELECT NUM_CPF, COUNT(*) FROM CADCNS
        WHERE NUM_CPF IS NOT NULL AND NUM_CPF != ''
        GROUP BY NUM_CPF HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"    Grupos encontrados: {len(grupos)}")
    mantido = deletados = 0
    for g in grupos:
        cur.execute("SELECT ID_CADCNS FROM CADCNS WHERE NUM_CPF = ? ORDER BY ID_CADCNS", (g[0],))
        ids = [r[0] for r in cur.fetchall()]
        m, d = merge_group_fb(ids, cur)
        mantido += m; deletados += d
    fb_con.commit()
    total_removidos += deletados
    print(f"    Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ── Fase 3: Duplicatas por CNS ────────────────────────────────────────────
    print("  Fase 3: Duplicatas por CNS...")
    cur.execute("""
        SELECT CNS, COUNT(*) FROM CADCNS
        WHERE CNS IS NOT NULL AND CNS != ''
        GROUP BY CNS HAVING COUNT(*) > 1
    """)
    grupos = cur.fetchall()
    print(f"    Grupos encontrados: {len(grupos)}")
    mantido = deletados = 0
    for g in grupos:
        cur.execute("SELECT ID_CADCNS FROM CADCNS WHERE CNS = ? ORDER BY ID_CADCNS", (g[0],))
        ids = [r[0] for r in cur.fetchall()]
        m, d = merge_group_fb(ids, cur)
        mantido += m; deletados += d
    fb_con.commit()
    total_removidos += deletados
    print(f"    Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ── Verificacao final ─────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM CADCNS")
    total_final = cur.fetchone()[0]

    print(f"  CADCNS antes:       {total_inicial}")
    print(f"  Registros removidos:{total_removidos}")
    print(f"  CADCNS depois:      {total_final}")

    cur.execute("""
        SELECT NUM_CPF, COUNT(*) FROM CADCNS
        WHERE NUM_CPF IS NOT NULL AND NUM_CPF != ''
        GROUP BY NUM_CPF HAVING COUNT(*) > 1
    """)
    restam_cpf = len(cur.fetchall())
    cur.execute("""
        SELECT CNS, COUNT(*) FROM CADCNS
        WHERE CNS IS NOT NULL AND CNS != ''
        GROUP BY CNS HAVING COUNT(*) > 1
    """)
    restam_cns = len(cur.fetchall())

    if restam_cpf or restam_cns:
        print(f"\n  ATENCAO: ainda restam duplicatas (por CPF: {restam_cpf} | por CNS: {restam_cns})")
    else:
        print("\n  Nenhuma duplicata restante. CADCNS limpo!")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 60)
    print("  PREPARACAO MENSAL BPA — HMPCF")
    print("  PostgreSQL -> Firebird + Deduplicacao")
    print("=" * 60 + "\n")

    # Conecta PostgreSQL
    try:
        pg_con = psycopg2.connect(**POSTGRES_CONFIG)
        print(f"PostgreSQL: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']} [OK]")
    except Exception as e:
        print(f"ERRO ao conectar no PostgreSQL: {e}")
        sys.exit(1)

    # Conecta Firebird
    try:
        fb_con = firebirdsql.connect(**FIREBIRD_CONFIG)
        print(f"Firebird:   {FIREBIRD_CONFIG['database']} [OK]\n")
    except Exception as e:
        print(f"ERRO ao conectar no Firebird: {e}")
        pg_con.close()
        sys.exit(1)

    try:
        etapa_migracao(pg_con, fb_con)
        etapa_deduplicar(fb_con)
    finally:
        for con in (fb_con, pg_con):
            try:
                con.close()
            except Exception:
                pass

    print("\n" + "=" * 60)
    print("  PREPARACAO CONCLUIDA! Firebird pronto para o BPA.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
