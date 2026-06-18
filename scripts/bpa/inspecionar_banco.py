"""
Inspeciona o banco Firebird de PRODUCAO (somente leitura).
NAO faz nenhuma escrita/alteracao no banco. Apenas SELECT.

Descoberta: TRIM() depende de UDF bloqueada pelo servidor
("Use of UDF library at location udflib.DLL is not allowed").
Por isso este script evita TRIM e usa apenas SELECT simples.
"""

import sys
import firebirdsql

DB_PATH = r"C:\BPA\BPAMAG.GDB"

LOG = []


def p(*args):
    txt = " ".join(str(a) for a in args)
    try:
        print(txt)
    except UnicodeEncodeError:
        print(txt.encode("ascii", "replace").decode("ascii"))
    LOG.append(txt)


con = firebirdsql.connect(
    host="localhost", database=DB_PATH,
    user="SYSDBA", password="masterkey", charset="WIN1252",
)
cur = con.cursor()

p("=== Teste: SELECT simples sem TRIM ===")
try:
    cur.execute("SELECT FIRST 3 CNS FROM CADCNS")
    for row in cur.fetchall():
        p("  CNS:", repr(row[0]))
    p("  OK - sem TRIM funciona")
except Exception as e:
    p("  FALHOU mesmo sem TRIM:", e)
    con.rollback()

p("\n=== Teste: SELECT com TRIM (confirmar se e isso) ===")
try:
    cur.execute("SELECT FIRST 1 TRIM(CNS) FROM CADCNS")
    cur.fetchall()
    p("  OK - TRIM funciona (nao era isso)")
except Exception as e:
    p("  FALHOU com TRIM (confirmado: TRIM usa UDF bloqueada):", e)
    con.rollback()

CADCNS_COLS = ["CNS", "NOME", "DTNASC", "SEXO", "RACA", "LOGPCN", "NUMPCN",
               "CPLPCN", "CEPPCN", "IBGE", "ETNIA", "NACIONALIDADE",
               "CO_LOGRAD", "BAIRRO_PCNTE", "DDTEL_PCNTE", "TEL_PCNTE",
               "EMAIL_PCNTE", "NUM_CPF"]

p("\n=== CADCNS — 5 pacientes reais (sem TRIM, usando CNS IS NOT NULL) ===")
try:
    cur.execute(f"""
        SELECT FIRST 5 {', '.join(CADCNS_COLS)}
        FROM CADCNS
        WHERE CNS IS NOT NULL AND CNS <> ''
    """)
    cols_cadcns = [d[0] for d in cur.description]
    for row in cur.fetchall():
        p("\n  ---")
        for col, val in zip(cols_cadcns, row):
            p(f"  {col:20} = {val!r}  ({type(val).__name__})")
except Exception as e:
    p("  ERRO:", e)
    con.rollback()

SPRD_COLS = ["PRD_CMP", "PRD_CNSMED", "PRD_CBO", "PRD_DTATEN", "PRD_FLH",
             "PRD_SEQ", "PRD_PA", "PRD_CNSPAC", "PRD_NMPAC", "PRD_DTNASC",
             "PRD_SEXO", "PRD_IBGE", "PRD_CID", "PRD_IDADE", "PRD_QT_P",
             "PRD_CATEN", "PRD_NAUT", "PRD_ORG", "PRD_RACA", "PRD_ETNIA",
             "PRD_NAC", "PRD_LOGRAD_PCNTE", "PRD_CEP_PCNTE", "PRD_END_PCNTE",
             "PRD_COMPL_PCNTE", "PRD_NUM_PCNTE", "PRD_BAIRRO_PCNTE",
             "PRD_DDTEL_PCNTE", "PRD_TEL_PCNTE", "PRD_EMAIL_PCNTE",
             "PRD_CPF_PCNTE"]

p("\n=== S_PRD — 5 registros reais ja digitados (sem TRIM) ===")
try:
    cur.execute(f"""
        SELECT FIRST 5 {', '.join(SPRD_COLS)}
        FROM S_PRD
        WHERE PRD_CNSPAC IS NOT NULL
    """)
    cols_sprd = [d[0] for d in cur.description]
    for row in cur.fetchall():
        p("\n  ---")
        for col, val in zip(cols_sprd, row):
            p(f"  {col:20} = {val!r}  ({type(val).__name__})")
except Exception as e:
    p("  ERRO:", e)
    con.rollback()

con.close()
p("\n=== FIM (somente leitura, nenhuma alteracao feita) ===")

with open("inspecao.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
