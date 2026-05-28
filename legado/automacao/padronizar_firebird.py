"""
Padroniza campos vazios/no CADCNS do Firebird com valores padrão.
=================================================================
Pode ser executado standalone em qualquer máquina com acesso ao GDB.
"""
import firebirdsql

FB = dict(
    host='localhost',
    database=r'C:\BPA\BPAMAG.GDB',
    user='SYSDBA',
    password='masterkey',
    charset='WIN1252'
)

PADROES = {
    'LOGPCN': "PRINCIPAL",
    'NUMPCN': "S/N",
    'BAIRRO_PCNTE': "CENTRO",
    'CEPPCN': "59575000",
    'IBGE': "240360",
    'CO_LOGRAD': "081",
    'RACA': "03",
}

con = firebirdsql.connect(**FB)
cur = con.cursor()

print("=" * 45)
print("       PADRONIZANDO CADCNS")
print("=" * 45)

total_afetados = 0

for campo, valor in PADROES.items():
    cur.execute(f"SELECT COUNT(*) FROM CADCNS WHERE {campo} IS NULL OR {campo} = ''")
    vazios = cur.fetchone()[0]
    if vazios == 0:
        print(f"  {campo:15s} OK  nenhum vazio")
        continue

    cur.execute(f"UPDATE CADCNS SET {campo} = ? WHERE {campo} IS NULL OR {campo} = ''", (valor,))
    con.commit()
    print(f"  {campo:15s} OK  {vazios} registros -> '{valor}'")
    total_afetados += vazios

# CO_LOGRAD deve ser 081 em TODOS os registros
cur.execute("SELECT COUNT(*) FROM CADCNS")
total = cur.fetchone()[0]
cur.execute("UPDATE CADCNS SET CO_LOGRAD = '081'")
con.commit()
print(f"  CO_LOGRAD        OK  {total} registros -> '081' (todos)")
total_afetados += total

con.close()

print("=" * 45)
print(f"  Total de campos corrigidos: {total_afetados}")
print("=" * 45)
