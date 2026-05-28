import sqlite3

path = r'C:\HMPCF-Automation-System\hospital.db'
conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("=== TABELAS ===")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    count = cur.fetchone()[0]
    print(f"  {t}: {count} registros")

for t in tables:
    print(f"\n=== SCHEMA: {t} ===")
    cur.execute(f"PRAGMA table_info([{t}])")
    cols = cur.fetchall()
    for col in cols:
        print(f"  cid={col[0]} name={col[1]:25s} type={col[2]:20s} notnull={col[3]} default={col[4]} pk={col[5]}")

# Amostra de todas as tabelas exceto pacientes (já sabemos o schema)
for t in tables:
    if t != 'pacientes':
        print(f"\n=== AMOSTRA: {t} (3 linhas) ===")
        cur.execute(f"SELECT * FROM [{t}] LIMIT 3")
        rows = cur.fetchall()
        if rows:
            print("  colunas:", list(rows[0].keys()))
            for r in rows:
                print(" ", dict(r))
        else:
            print("  (vazia)")

conn.close()
print("\nDone.")
