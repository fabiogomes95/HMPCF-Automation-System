"""
CORRECAO_COMPLETA.py — Ferramenta interativa de correcao cadastral
====================================================================
Escaneia hospital.db (SQLite) e BPAMAG.GDB (Firebird) em busca de:
  - Pacientes duplicados (mesmo nome + data nascimento, CPF/CNS diferentes)
  - Registros com formatacao inconsistente (CPF 105.423.924-02 vs 10542392402)
  - Registros no Firebird sem CPF

Nao executa nada sem confirmacao do usuario.
"""

import sqlite3
import firebirdsql
import re
import os

FB = dict(host='localhost', database=r'C:\BPA\BPAMAG.GDB', user='SYSDBA', password='masterkey', charset='WIN1252')
SQLITE = r'C:\Users\User\Documents\HMPCF-Automation-System\hospital.db'


def limpar_numero(v):
    return re.sub(r'\D', '', str(v)) if v else ''


def pausa():
    print()
    input("Pressione ENTER para continuar...")


# ===================================================================
# CONEXOES
# ===================================================================

sq = sqlite3.connect(SQLITE)
sq.row_factory = sqlite3.Row
csq = sq.cursor()

try:
    fb = firebirdsql.connect(**FB)
    cfb = fb.cursor()
except Exception as e:
    print(f"ERRO ao conectar no Firebird: {e}")
    fb = None

# ===================================================================
# 1. SCAN SQLITE — pacientes com CPF/CNS formatados inconsistentes
# ===================================================================

print("=" * 65)
print("  SCAN 1: REGISTROS COM FORMATACAO INCONSISTENTE (SQLITE)")
print("=" * 65)

csq.execute("SELECT rowid, CNS, NUM_CPF, NOME, DTNASC FROM pacientes ORDER BY NOME")
todos = csq.fetchall()

agrupados = {}  # (clean_cpf or clean_cns) -> [rows]

for r in todos:
    cns_clean = limpar_numero(r['CNS'])
    cpf_clean = limpar_numero(r['NUM_CPF'])
    if cns_clean:
        agrupados.setdefault(('CNS', cns_clean), []).append(r)
    if cpf_clean:
        agrupados.setdefault(('CPF', cpf_clean), []).append(r)

inconsistencias = []
for chave, grupo in agrupados.items():
    if len(grupo) > 1:
        # Verifica se diferem por formatacao (mesmo numero, escrita diferente)
        valores_raw = set()
        for r in grupo:
            v = r['CNS'] if chave[0] == 'CNS' else r['NUM_CPF']
            valores_raw.add(v)
        if len(valores_raw) > 1:
            inconsistencias.append((chave, grupo))

if not inconsistencias:
    print("  Nenhuma inconsistencia de formatacao encontrada.")
else:
    for chave, grupo in inconsistencias:
        print(f"\n  [{chave[0]}] {chave[1]}")
        for r in grupo:
            raw = r['CNS'] if chave[0] == 'CNS' else r['NUM_CPF']
            print(f"    rowid={r['rowid']:>6} | {raw:20s} | {r['NOME'][:40]:40s} | {r['DTNASC'] or '(sem dt)'}")
        resp = input("  Unificar (manter o sem formatacao, deletar formatado)? [s/N] ").strip().lower()
        if resp == 's':
            # Mantem o primeiro sem formatacao, deleta os outros
            alvo = None
            for r in grupo:
                raw = r['CNS'] if chave[0] == 'CNS' else r['NUM_CPF']
                if raw == chave[1]:
                    alvo = (r['rowid'], raw)
                    break
            if not alvo:
                alvo = (grupo[0]['rowid'], chave[1])

            for r in grupo:
                if r['rowid'] == alvo[0]:
                    continue
                raw_cns = r['CNS']
                raw_cpf = r['NUM_CPF']
                if chave[0] == 'CNS':
                    csq.execute("UPDATE atendimentos SET sus = ? WHERE sus = ?", (chave[1], raw_cns))
                    print(f"    Atendimentos atualizados: SUS {raw_cns} -> {chave[1]} ({csq.rowcount})")
                else:
                    csq.execute("UPDATE atendimentos SET cpf = ? WHERE cpf = ?", (chave[1], raw_cpf))
                    print(f"    Atendimentos atualizados: CPF {raw_cpf} -> {chave[1]} ({csq.rowcount})")
                csq.execute("DELETE FROM pacientes WHERE rowid = ?", (r['rowid'],))
                print(f"    Registro rowid={r['rowid']} removido.")
            sq.commit()
            print("  OK")
        else:
            print("  Pulado.")

# ===================================================================
# 2. SCAN SQLITE — pacientes com mesmo nome+dt e CPF/CNS diferentes
# ===================================================================

print()
print("=" * 65)
print("  SCAN 2: POSSIVEIS DUPLICATAS (MESMO NOME + DATA) (SQLITE)")
print("=" * 65)

csq.execute("""
    SELECT rowid, CNS, NUM_CPF, NOME, DTNASC, SEXO, LOGPCN, NUMPCN, BAIRRO_PCNTE
    FROM pacientes
    WHERE NOME IS NOT NULL AND NOME != ''
      AND DTNASC IS NOT NULL AND DTNASC != ''
    ORDER BY NOME, DTNASC
""")
todos = csq.fetchall()

duplicatas = {}
for r in todos:
    chave = (r['NOME'].strip().upper(), str(r['DTNASC']).strip())
    duplicatas.setdefault(chave, []).append(r)

achou_dup = False
for chave, grupo in duplicatas.items():
    if len(grupo) < 2:
        continue
    # Verifica se tem CPF/CNS diferentes entre si
    cpfs = {limpar_numero(r['NUM_CPF']) for r in grupo}
    cnss = {limpar_numero(r['CNS']) for r in grupo}
    if len(cpfs | cnss) < 2:
        continue  # mesmo CPF/CNS, ja tratado no scan 1

    achou_dup = True
    print(f"\n  NOME: {chave[0][:50]:50s} | DTNASC: {chave[1]}")
    for r in grupo:
        print(f"    rowid={r['rowid']:>6} | CPF={r['NUM_CPF'] or '(vazio)':16s} | CNS={r['CNS'] or '(vazio)':20s} | End: {r['LOGPCN'] or '-'}, {r['NUMPCN'] or '-'}, {r['BAIRRO_PCNTE'] or '-'}")

    # Conta atendimentos de cada CPF/CNS
    print("    Atendimentos:")
    for r in grupo:
        cpf = limpar_numero(r['NUM_CPF'])
        cns = limpar_numero(r['CNS'])
        total = 0
        if cpf:
            total += csq.execute("SELECT COUNT(*) FROM atendimentos WHERE cpf LIKE ?", (f'%{cpf}%',)).fetchone()[0]
        if cns:
            total += csq.execute("SELECT COUNT(*) FROM atendimentos WHERE sus LIKE ?", (f'%{cns}%',)).fetchone()[0]
        print(f"      rowid={r['rowid']:>6} -> {total} atendimento(s)")

    resp = input("  \n  Escolha o rowid PARA MANTER (ou 0 para pular): ").strip()
    if resp.isdigit() and int(resp) > 0:
        manter_id = int(resp)
        manter = None
        for r in grupo:
            if r['rowid'] == manter_id:
                manter = r
                break
        if not manter:
            print("  rowid invalido, pulando.")
            continue

        for r in grupo:
            if r['rowid'] == manter_id:
                continue
            # Migrar atendimentos do CPF/CNS secundario para o principal
            cpf_sec = limpar_numero(r['NUM_CPF'])
            cns_sec = limpar_numero(r['CNS'])
            cpf_pri = limpar_numero(manter['NUM_CPF'])
            cns_pri = limpar_numero(manter['CNS'])

            if cpf_sec and cpf_pri and cpf_sec != cpf_pri:
                # Tenta achar qual CPF literal esta no atendimentos
                csq.execute("SELECT DISTINCT cpf FROM atendimentos WHERE cpf LIKE ?", (f'%{cpf_sec}%',))
                for (cpf_literal,) in csq.fetchall():
                    csq.execute("UPDATE atendimentos SET cpf = ? WHERE cpf = ?", (cpf_pri, cpf_literal))
                    print(f"    Atendimentos migrados: CPF {cpf_literal} -> {cpf_pri} ({csq.rowcount})")

            if cns_sec and cns_pri and cns_sec != cns_pri:
                csq.execute("SELECT DISTINCT sus FROM atendimentos WHERE sus LIKE ?", (f'%{cns_sec}%',))
                for (sus_literal,) in csq.fetchall():
                    csq.execute("UPDATE atendimentos SET sus = ? WHERE sus = ?", (cns_pri, sus_literal))
                    print(f"    Atendimentos migrados: SUS {sus_literal} -> {cns_pri} ({csq.rowcount})")

            csq.execute("DELETE FROM pacientes WHERE rowid = ?", (r['rowid'],))
            print(f"    Registro rowid={r['rowid']} removido.")
        sq.commit()
        print("  OK")
    else:
        print("  Pulado.")

if not achou_dup:
    print("  Nenhuma duplicata encontrada.")

# ===================================================================
# 3. SCAN FIREBIRD — registros sem CPF
# ===================================================================

if fb:
    print()
    print("=" * 65)
    print("  SCAN 3: REGISTROS SEM CPF NO FIREBIRD (CADCNS)")
    print("=" * 65)

    cfb.execute("SELECT ID_CADCNS, NUM_CPF, CNS, NOME, DTNASC FROM CADCNS WHERE NUM_CPF IS NULL OR NUM_CPF = ''")
    sem_cpf = cfb.fetchall()

    if not sem_cpf:
        print("  Nenhum registro sem CPF encontrado.")
    else:
        print(f"  Total de registros sem CPF: {len(sem_cpf)}")
        for r in sem_cpf[:20]:
            print(f"    ID={r[0]:>6} | CNS={r[2] or '(vazio)':20s} | {r[3][:40] if r[3] else '(sem nome)':40s} | DT={r[4] or ''}")
        if len(sem_cpf) > 20:
            print(f"    ... e mais {len(sem_cpf) - 20} registro(s)")

        resp = input("\n  Buscar CPF no SQLite para esses registros? [s/N] ").strip().lower()
        if resp == 's':
            for rfb in sem_cpf:
                cns_fb = limpar_numero(rfb[2]) if rfb[2] else ''
                if cns_fb:
                    csq.execute("SELECT NUM_CPF FROM pacientes WHERE CNS LIKE ? LIMIT 1", (f'%{cns_fb}%',))
                    row = csq.fetchone()
                    if row and limpar_numero(row[0]):
                        cpf_encontrado = limpar_numero(row[0])
                        print(f"    ID={rfb[0]}: CPF encontrado no SQLite = {cpf_encontrado}")
                        resp2 = input(f"    Atualizar Firebird ID={rfb[0]} com CPF {cpf_encontrado}? [s/N] ").strip().lower()
                        if resp2 == 's':
                            cfb.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE ID_CADCNS = ?", (cpf_encontrado, rfb[0]))
                            fb.commit()
                            print("    OK")
                        else:
                            print("    Pulado.")
                    else:
                        nome_fb = rfb[3].strip().upper() if rfb[3] else ''
                        if nome_fb:
                            csq.execute("SELECT NUM_CPF, CNS FROM pacientes WHERE NOME LIKE ? LIMIT 1", (f'%{nome_fb[:20]}%',))
                            row = csq.fetchone()
                            if row and limpar_numero(row[0]):
                                print(f"    ID={rfb[0]}: Possivel CPF pelo nome = {limpar_numero(row[0])} (CNS SQLite={row[1]})")
                                resp2 = input(f"    Atualizar? [s/N] ").strip().lower()
                                if resp2 == 's':
                                    cfb.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE ID_CADCNS = ?", (limpar_numero(row[0]), rfb[0]))
                                    fb.commit()
                                    print("    OK")
                                else:
                                    print("    Pulado.")
                            else:
                                print(f"    ID={rfb[0]}: sem CPF correspondente no SQLite")
                else:
                    print(f"    ID={rfb[0]}: sem CNS, pulando.")

# ===================================================================
# 4. SCAN FIREBIRD — registros que existem nos dois bancos com CPF diferentes
# ===================================================================

if fb:
    print()
    print("=" * 65)
    print("  SCAN 4: MESMO PACIENTE EM SQLITE E FIREBIRD COM CPF DIVERGENTE")
    print("=" * 65)

    cfb.execute("SELECT ID_CADCNS, NUM_CPF, CNS, NOME, DTNASC FROM CADCNS WHERE NUM_CPF IS NOT NULL AND NUM_CPF != ''")
    fb_todos = cfb.fetchall()

    conflitos = []
    for rfb in fb_todos:
        cpf_fb = limpar_numero(rfb[1])
        cns_fb = limpar_numero(rfb[2]) if rfb[2] else ''
        if cpf_fb:
            csq.execute("SELECT NUM_CPF, CNS, NOME FROM pacientes WHERE NUM_CPF LIKE ? LIMIT 1", (f'%{cpf_fb}%',))
            row = csq.fetchone()
            if row:
                cpf_sq = limpar_numero(row[0])
                if cpf_fb != cpf_sq:
                    conflitos.append((rfb, row))
            elif cns_fb:
                csq.execute("SELECT NUM_CPF, CNS, NOME FROM pacientes WHERE CNS LIKE ? LIMIT 1", (f'%{cns_fb}%',))
                row = csq.fetchone()
                if row:
                    conflitos.append((rfb, row))

    if not conflitos:
        print("  Nenhum conflito encontrado.")
    else:
        for rfb, rsq in conflitos:
            print(f"\n  Firebird ID={rfb[0]} | CPF={rfb[1]} | CNS={rfb[2] or '(vazio)'} | {rfb[3]}")
            print(f"  SQLite            | CPF={rsq[0] or '(vazio)'} | CNS={rsq[1] or '(vazio)'} | {rsq[2]}")
            resp = input("  Corrigir Firebird para igualar ao SQLite? [s/N] ").strip().lower()
            if resp == 's':
                cpf_alvo = limpar_numero(rsq[0]) or limpar_numero(rfb[1])
                cfb.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE ID_CADCNS = ?", (cpf_alvo, rfb[0]))
                fb.commit()
                print("  OK")
            else:
                print("  Pulado.")

# ===================================================================
# RESUMO FINAL
# ===================================================================

print()
print("=" * 65)
print("  SCAN CONCLUIDO")
print("=" * 65)

csq.execute("SELECT COUNT(*) FROM pacientes")
print(f"  Total pacientes no SQLite: {csq.fetchone()[0]}")

if fb:
    cfb.execute("SELECT COUNT(*) FROM CADCNS")
    print(f"  Total registros no Firebird: {cfb.fetchone()[0]}")

sq.close()
if fb:
    fb.close()
print()
