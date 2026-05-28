"""
REPARAR_FIREBIRD.py — Reparo de registros corrompidos no BPAMAG.GDB
====================================================================
Ferramenta exclusiva de REPARO e CORRECAO de registros antigos no
banco Firebird (CADCNS). Nao le SQLite, nao faz inserts. Apenas
corrige campos nulos/zerados que disparam erro 'Could not convert'.

CORRECOES:
  1. ID_CADCNS nulo      -> Gera sequencial novo (MAX + 1)
  2. CO_LOGRAD nulo/zero -> '081'
  3. LOGPCN nulo/vazio   -> 'PRINCIPAL'
  4. NUMPCN nulo/vazio   -> 'S/N'
  5. BAIRRO_PCNTE nulo/vazio -> 'CENTRO'
  6. SEXO invalido       -> 'I'
  7. RACA nula/vazia     -> '03'
"""

import firebirdsql

# ── CONFIGURACAO ──────────────────────────────────────────────────────────────

FIREBIRD_CONFIG = dict(
    host='localhost',
    database=r'C:\BPA\BPAMAG.GDB',
    user='SYSDBA',
    password='masterkey',
    charset='WIN1252'
)

# ── CONEXAO ───────────────────────────────────────────────────────────────────

print("=" * 60)
print("  REPARAR FIREBIRD — Corrigindo registros corrompidos CADCNS")
print("=" * 60)

try:
    con = firebirdsql.connect(**FIREBIRD_CONFIG)
    cur = con.cursor()
    print("\nConectado ao BPAMAG.GDB com firebirdsql.\n")
except Exception as e:
    print(f"ERRO ao conectar no Firebird: {e}")
    exit(1)

total_geral = 0

# ── 1. CORRIGIR ID_CADCNS NULO ───────────────────────────────────────────────

print("--- 1. Corrigindo ID_CADCNS nulo ---")

try:
    cur.execute("SELECT COUNT(*) FROM CADCNS WHERE ID_CADCNS IS NULL")
    total_null = cur.fetchone()[0]
    print(f"  Registros com ID_CADCNS nulo: {total_null}")

    if total_null > 0:
        cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
        max_id = cur.fetchone()[0]
        novo_id = max_id if max_id is not None else 0
        print(f"  Maior ID existente: {max_id}  |  Iniciando em: {novo_id + 1}")

        cur.execute("CREATE GENERATOR GEN_TEMP_ID")
        cur.execute(f"SET GENERATOR GEN_TEMP_ID TO {novo_id}")
        cur.execute("""
            UPDATE CADCNS
            SET ID_CADCNS = GEN_ID(GEN_TEMP_ID, 1)
            WHERE ID_CADCNS IS NULL
        """)
        corrigidos_id = cur.rowcount
        cur.execute("DROP GENERATOR GEN_TEMP_ID")
        con.commit()
        print(f"  ID_CADCNS corrigidos: {corrigidos_id}")
        total_geral += corrigidos_id
    else:
        print("  Nenhum ID nulo encontrado.")

except Exception as e:
    try:
        cur.execute("DROP GENERATOR GEN_TEMP_ID")
    except Exception:
        pass
    con.rollback()
    print(f"  ERRO ao corrigir ID_CADCNS: {e}")

# ── 2. CORRIGIR CO_LOGRAD ────────────────────────────────────────────────────

print("\n--- 2. Corrigindo CO_LOGRAD ---")

try:
    cur.execute("""
        SELECT COUNT(*) FROM CADCNS
        WHERE CO_LOGRAD IS NULL
           OR CO_LOGRAD = ''
           OR CO_LOGRAD = '000'
           OR CO_LOGRAD = '0'
    """)
    total = cur.fetchone()[0]
    print(f"  Registros com CO_LOGRAD invalido: {total}")

    if total > 0:
        cur.execute("""
            UPDATE CADCNS SET CO_LOGRAD = '081'
            WHERE CO_LOGRAD IS NULL
               OR CO_LOGRAD = ''
               OR CO_LOGRAD = '000'
               OR CO_LOGRAD = '0'
        """)
        con.commit()
        print(f"  CO_LOGRAD corrigidos: {total}")
        total_geral += total
    else:
        print("  Todos ja estao corretos.")

except Exception as e:
    print(f"  ERRO ao corrigir CO_LOGRAD: {e}")

# ── 3. CORRIGIR LOGPCN ───────────────────────────────────────────────────────

print("\n--- 3. Corrigindo LOGPCN (Endereco) ---")

try:
    cur.execute("""
        SELECT COUNT(*) FROM CADCNS
        WHERE LOGPCN IS NULL OR LOGPCN = ''
    """)
    total = cur.fetchone()[0]
    print(f"  Registros com LOGPCN vazio: {total}")

    if total > 0:
        cur.execute("""
            UPDATE CADCNS SET LOGPCN = 'PRINCIPAL'
            WHERE LOGPCN IS NULL OR LOGPCN = ''
        """)
        con.commit()
        print(f"  LOGPCN corrigidos: {total}")
        total_geral += total
    else:
        print("  Todos ja estao preenchidos.")

except Exception as e:
    print(f"  ERRO ao corrigir LOGPCN: {e}")

# ── 4. CORRIGIR NUMPCN ───────────────────────────────────────────────────────

print("\n--- 4. Corrigindo NUMPCN (Numero) ---")

try:
    cur.execute("""
        SELECT COUNT(*) FROM CADCNS
        WHERE NUMPCN IS NULL OR NUMPCN = ''
    """)
    total = cur.fetchone()[0]
    print(f"  Registros com NUMPCN vazio: {total}")

    if total > 0:
        cur.execute("""
            UPDATE CADCNS SET NUMPCN = 'S/N'
            WHERE NUMPCN IS NULL OR NUMPCN = ''
        """)
        con.commit()
        print(f"  NUMPCN corrigidos: {total}")
        total_geral += total
    else:
        print("  Todos ja estao preenchidos.")

except Exception as e:
    print(f"  ERRO ao corrigir NUMPCN: {e}")

# ── 5. CORRIGIR BAIRRO_PCNTE ─────────────────────────────────────────────────

print("\n--- 5. Corrigindo BAIRRO_PCNTE (Bairro) ---")

try:
    cur.execute("""
        SELECT COUNT(*) FROM CADCNS
        WHERE BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = ''
    """)
    total = cur.fetchone()[0]
    print(f"  Registros com BAIRRO_PCNTE vazio: {total}")

    if total > 0:
        cur.execute("""
            UPDATE CADCNS SET BAIRRO_PCNTE = 'CENTRO'
            WHERE BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = ''
        """)
        con.commit()
        print(f"  BAIRRO_PCNTE corrigidos: {total}")
        total_geral += total
    else:
        print("  Todos ja estao preenchidos.")

except Exception as e:
    print(f"  ERRO ao corrigir BAIRRO_PCNTE: {e}")

# ── 6. CORRIGIR SEXO ─────────────────────────────────────────────────────────

print("\n--- 6. Corrigindo SEXO ---")

try:
    cur.execute("""
        SELECT COUNT(*) FROM CADCNS
        WHERE SEXO IS NULL
           OR SEXO = ''
           OR (SEXO NOT IN ('M', 'F', 'I'))
    """)
    total = cur.fetchone()[0]
    print(f"  Registros com SEXO invalido: {total}")

    if total > 0:
        cur.execute("""
            UPDATE CADCNS SET SEXO = 'I'
            WHERE SEXO IS NULL
               OR SEXO = ''
               OR (SEXO NOT IN ('M', 'F', 'I'))
        """)
        con.commit()
        print(f"  SEXO corrigidos: {total}")
        total_geral += total
    else:
        print("  Todos ja estao validos.")

except Exception as e:
    print(f"  ERRO ao corrigir SEXO: {e}")

# ── 7. CORRIGIR RACA ─────────────────────────────────────────────────────────

print("\n--- 7. Corrigindo RACA ---")

try:
    cur.execute("""
        SELECT COUNT(*) FROM CADCNS
        WHERE RACA IS NULL OR RACA = ''
    """)
    total = cur.fetchone()[0]
    print(f"  Registros com RACA vazia: {total}")

    if total > 0:
        cur.execute("""
            UPDATE CADCNS SET RACA = '03'
            WHERE RACA IS NULL OR RACA = ''
        """)
        con.commit()
        print(f"  RACA corrigidos: {total}")
        total_geral += total
    else:
        print("  Todos ja estao preenchidos.")

except Exception as e:
    print(f"  ERRO ao corrigir RACA: {e}")

# ── RESUMO FINAL ──────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("        RESUMO DO REPARO")
print("=" * 60)
print(f"  Total de correcoes aplicadas: {total_geral}")
print("=" * 60)

# ── VERIFICACAO POS-REPARO ───────────────────────────────────────────────────

print("\n--- Verificacao pos-reparo ---")

try:
    cur.execute("SELECT COUNT(*) FROM CADCNS")
    print(f"  Total de registros: {cur.fetchone()[0]}")

    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(CASE WHEN ID_CADCNS IS NULL THEN 1 END) AS id_null,
            COUNT(CASE WHEN CO_LOGRAD IS NULL OR CO_LOGRAD = '' OR CO_LOGRAD = '000' OR CO_LOGRAD = '0' THEN 1 END) AS co_lograd_inv,
            COUNT(CASE WHEN LOGPCN IS NULL OR LOGPCN = '' THEN 1 END) AS sem_log,
            COUNT(CASE WHEN NUMPCN IS NULL OR NUMPCN = '' THEN 1 END) AS sem_num,
            COUNT(CASE WHEN BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = '' THEN 1 END) AS sem_bairro,
            COUNT(CASE WHEN SEXO IS NULL OR SEXO = '' OR SEXO NOT IN ('M', 'F', 'I') THEN 1 END) AS sexo_inv,
            COUNT(CASE WHEN RACA IS NULL OR RACA = '' THEN 1 END) AS sem_raca
        FROM CADCNS
    """)
    r = cur.fetchone()
    print(f"  ID_CADCNS nulo:             {r[1]}")
    print(f"  CO_LOGRAD invalido:         {r[2]}")
    print(f"  LOGPCN vazio:               {r[3]}")
    print(f"  NUMPCN vazio:               {r[4]}")
    print(f"  BAIRRO_PCNTE vazio:         {r[5]}")
    print(f"  SEXO invalido:              {r[6]}")
    print(f"  RACA vazia:                 {r[7]}")

    if all(x == 0 for x in r[1:]):
        print("\n  >>> REPARO CONCLUIDO — Nenhum campo invalido restante <<<")
    else:
        print("\n  >>> AVISO: Ainda ha campos invalidos nao corrigidos <<<")

except Exception as e:
    print(f"  Erro na verificacao: {e}")

# ── FECHAR CONEXAO ───────────────────────────────────────────────────────────

try:
    con.close()
except Exception:
    pass

print("\nReparo finalizado!")
print("=" * 60)
