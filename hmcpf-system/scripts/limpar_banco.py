"""
Limpa CPFs/SUS formatados, remove duplicatas (por CPF e por nome+DN),
remove pacientes sem nome e com CPF inválido.

USO:
    python scripts/fix_cpf_duplicates.py              # procura hospital.db na raiz
    python scripts/fix_cpf_duplicates.py "C:\\caminho\\hospital.db"
"""
import sqlite3, re, sys, os
from collections import defaultdict

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else None

def clean_cpf(cpf):
    return re.sub(r'\D', '', cpf or '')

def row_completeness(row):
    return sum(1 for k, v in dict(row).items() if v not in (None, '', 'None'))

def _find_db():
    if DB_PATH and os.path.exists(DB_PATH):
        return DB_PATH
    candidates = [
        "hospital.db",
        os.path.join("..", "hospital.db"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    print("ERRO: hospital.db nao encontrado! Passe o caminho como argumento.")
    print("  python fix_cpf_duplicates.py C:\\caminho\\hospital.db")
    sys.exit(1)

def apply_fix():
    db_path = _find_db()
    print(f"Banco: {db_path}\n")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # === 1. Remover duplicatas pelo mesmo CPF ===
    print("=== 1. Removendo duplicatas por CPF ===\n")
    cur.execute("SELECT rowid, cpf FROM pacientes WHERE cpf != ''")
    todos = cur.fetchall()
    groups = defaultdict(list)
    for r in todos:
        clean = clean_cpf(r['cpf'])
        if clean:
            groups[clean].append((r['rowid'], r['cpf']))

    dupes = {cpf: rows for cpf, rows in groups.items() if len(rows) > 1}
    removed = 0
    merged = 0

    for clean_cpf_val, rows in dupes.items():
        rows_info = []
        for rid, original_cpf in rows:
            cur.execute("SELECT * FROM pacientes WHERE rowid = ?", (rid,))
            rows_info.append((rid, original_cpf, row_completeness(cur.fetchone())))
        rows_info.sort(key=lambda x: -x[2])
        keeper_id = rows_info[0][0]
        to_delete = [(d[0], d[1]) for d in rows_info[1:]]

        for del_id, del_cpf in to_delete:
            cur.execute("UPDATE atendimentos SET cpf = ? WHERE cpf = ?", (clean_cpf_val, del_cpf))
            merged += cur.rowcount
            cur.execute("DELETE FROM pacientes WHERE rowid = ?", (del_id,))
            removed += 1
            print(f"  CPF {clean_cpf_val}: deletado rowid={del_id}, atendimentos movidos")

    conn.commit()
    print(f"\n  Duplicatas removidas: {removed}, atendimentos relocados: {merged}")

    # === 2. Normalizar CPFs (remover formatação) ===
    print("\n=== 2. Normalizando CPFs ===\n")
    cur.execute("SELECT rowid, cpf FROM pacientes WHERE cpf != ''")
    remaining = cur.fetchall()
    fixed = 0
    for r in remaining:
        clean = clean_cpf(r['cpf'])
        if clean and clean != r['cpf']:
            cur.execute("UPDATE pacientes SET cpf = ? WHERE rowid = ?", (clean, r['rowid']))
            fixed += 1
    conn.commit()
    print(f"  CPFs normalizados em pacientes: {fixed}")

    # Normalizar também na tabela atendimentos
    cur.execute("SELECT id, cpf FROM atendimentos WHERE cpf != ''")
    atd = cur.fetchall()
    fixed_atd = 0
    for rid, cpf in atd:
        c = clean_cpf(cpf)
        if c != cpf:
            cur.execute("UPDATE atendimentos SET cpf = ? WHERE id = ?", (c, rid))
            fixed_atd += 1
    conn.commit()
    print(f"  CPFs normalizados em atendimentos: {fixed_atd}")

    # === 3. Remover duplicatas por nome + DN ===
    print("\n=== 3. Removendo duplicatas por nome+DN ===\n")
    cur.execute("SELECT rowid, nome, dn, cpf FROM pacientes WHERE nome != '' AND nome IS NOT NULL AND dn != '' AND dn IS NOT NULL")
    pacientes = cur.fetchall()

    nome_dn_groups = defaultdict(list)
    for r in pacientes:
        key = (r['nome'].strip().upper(), r['dn'].strip())
        if key[0] and key[1]:
            nome_dn_groups[key].append((r['rowid'], r['cpf']))

    nome_dn_dupes = {k: v for k, v in nome_dn_groups.items() if len(v) > 1}
    removed2 = 0
    merged2 = 0

    for (nome, dn), rows in nome_dn_dupes.items():
        rows_info = []
        for rid, cpf in rows:
            cur.execute("SELECT * FROM pacientes WHERE rowid = ?", (rid,))
            rows_info.append((rid, cpf, row_completeness(cur.fetchone())))
        rows_info.sort(key=lambda x: -x[2])
        keeper_id = rows_info[0][0]
        keeper_cpf = rows_info[0][1]
        to_delete = [(d[0], d[1]) for d in rows_info[1:]]

        for del_id, del_cpf in to_delete:
            cur.execute("UPDATE atendimentos SET cpf = ? WHERE cpf = ?", (keeper_cpf, del_cpf))
            merged2 += cur.rowcount
            cur.execute("DELETE FROM pacientes WHERE rowid = ?", (del_id,))
            removed2 += 1
            print(f"  '{nome}' DN={dn}: deletado rowid={del_id} (CPF {del_cpf}), mantido rowid={keeper_id} (CPF {keeper_cpf})")

    conn.commit()
    print(f"\n  Duplicatas por nome+DN removidas: {removed2}, atendimentos relocados: {merged2}")

    # === 4. Normalizar SUS (remover espaços/pontos) ===
    print("\n=== 4. Normalizando SUS ===\n")
    cur.execute("SELECT rowid, sus FROM pacientes WHERE sus != '' AND sus IS NOT NULL AND (sus LIKE '% %' OR sus LIKE '%-%' OR sus LIKE '%.%')")
    com_formatacao = cur.fetchall()
    sus_fixed = 0
    for r in com_formatacao:
        c = clean_cpf(r['sus'])
        if c != r['sus']:
            cur.execute("UPDATE pacientes SET sus = ? WHERE rowid = ?", (c, r['rowid']))
            sus_fixed += 1
    conn.commit()
    print(f"  SUS normalizados: {sus_fixed}")

    # Limpar SUS inválidos (tamanho != 15) — mantém CPF, apaga só o SUS
    cur.execute("SELECT COUNT(*) FROM pacientes WHERE sus != '' AND sus IS NOT NULL AND length(sus) != 15")
    sus_invalidos = cur.fetchone()[0]
    if sus_invalidos:
        cur.execute("UPDATE pacientes SET sus = '' WHERE sus != '' AND sus IS NOT NULL AND length(sus) != 15")
        conn.commit()
        print(f"  SUS inválidos limpos: {sus_invalidos}")
    else:
        print("  Nenhum SUS inválido")

    # === 5. Remover pacientes sem nome ===
    print("\n=== 5. Removendo pacientes sem nome ===\n")
    cur.execute("SELECT cpf FROM pacientes WHERE nome = '' OR nome IS NULL")
    sem_nome = [r['cpf'] for r in cur.fetchall()]
    if sem_nome:
        placeholders = ','.join('?' * len(sem_nome))
        cur.execute(f"DELETE FROM atendimentos WHERE cpf IN ({placeholders})", sem_nome)
        d1 = cur.rowcount
        cur.execute(f"DELETE FROM pacientes WHERE cpf IN ({placeholders})", sem_nome)
        d2 = cur.rowcount
        conn.commit()
        print(f"  Atendimentos removidos: {d1}")
        print(f"  Pacientes removidos: {d2}")
    else:
        print("  Nenhum encontrado")

    # === 6. Remover pacientes com CPF inválido ===
    print("\n=== 6. Removendo pacientes com CPF inválido ===\n")
    cur.execute("SELECT cpf FROM pacientes WHERE cpf != '' AND length(cpf) != 11")
    cpf_invalid = [r['cpf'] for r in cur.fetchall()]
    if cpf_invalid:
        placeholders = ','.join('?' * len(cpf_invalid))
        cur.execute(f"DELETE FROM atendimentos WHERE cpf IN ({placeholders})", cpf_invalid)
        d1 = cur.rowcount
        cur.execute(f"DELETE FROM pacientes WHERE cpf IN ({placeholders})", cpf_invalid)
        d2 = cur.rowcount
        conn.commit()
        print(f"  Atendimentos removidos: {d1}")
        print(f"  Pacientes removidos: {d2}")
    else:
        print("  Nenhum encontrado")

    # === 7. Verificar resultado ===
    print("\n=== 7. Verificando resultado ===\n")
    cur.execute("SELECT cpf, COUNT(*) as cnt FROM pacientes GROUP BY cpf HAVING cnt > 1")
    remaining_dupes = cur.fetchall()
    if remaining_dupes:
        print(f"ATENCAO: {len(remaining_dupes)} CPFs ainda duplicados!")
        for r in remaining_dupes:
            print(f"  CPF: {r['cpf']} ({r['cnt']}x)")
    else:
        print("Nenhuma duplicata por CPF!")

    cur.execute("SELECT nome, dn, COUNT(*) as cnt FROM pacientes WHERE nome != '' AND dn != '' GROUP BY nome, dn HAVING cnt > 1")
    remaining_nome_dn = cur.fetchall()
    if remaining_nome_dn:
        print(f"\nATENCAO: {len(remaining_nome_dn)} grupos nome+DN ainda duplicados!")
        for r in remaining_nome_dn:
            print(f"  '{r['nome']}' DN={r['dn']} ({r['cnt']}x)")
    else:
        print("Nenhuma duplicata por nome+DN!")

    cur.execute("SELECT COUNT(*) FROM pacientes WHERE cpf LIKE '%.%' OR cpf LIKE '%-%' OR cpf LIKE '% %'")
    formatted = cur.fetchone()[0]
    if formatted:
        print(f"\nAinda ha {formatted} CPFs formatados!")
    else:
        print("Todos os CPFs estao normalizados!")

    cur.execute("SELECT COUNT(*) FROM pacientes WHERE sus LIKE '% %' OR sus LIKE '%-%' OR sus LIKE '%.%'")
    sus_format = cur.fetchone()[0]
    if sus_format:
        print(f"Ainda ha {sus_format} SUS formatados!")
    else:
        print("Todos os SUS estao normalizados!")

    cur.execute("SELECT COUNT(*) FROM pacientes WHERE nome = '' OR nome IS NULL")
    sem_nome = cur.fetchone()[0]
    if sem_nome:
        print(f"Ainda ha {sem_nome} pacientes sem nome!")
    else:
        print("Nenhum paciente sem nome!")

    cur.execute("SELECT COUNT(*) FROM pacientes WHERE cpf != '' AND length(cpf) != 11")
    cpf_inv = cur.fetchone()[0]
    if cpf_inv:
        print(f"Ainda ha {cpf_inv} CPFs com tamanho invalido!")
    else:
        print("Todos os CPFs tem 11 digitos!")

    cur.execute("SELECT COUNT(*) FROM atendimentos WHERE cpf NOT IN (SELECT cpf FROM pacientes)")
    orfaos = cur.fetchone()[0]
    if orfaos:
        print(f"Ainda ha {orfaos} atendimentos orfaos!")
    else:
        print("Nenhum atendimento orfao!")

    conn.close()
    print(f"\nPronto! Total de {removed+removed2} registros removidos.")

if __name__ == '__main__':
    confirm = input("ISSO VAI ALTERAR O BANCO DE DADOS! Confirmar? (s/N): ")
    if confirm.lower() == 's':
        apply_fix()
    else:
        print("Cancelado.")
