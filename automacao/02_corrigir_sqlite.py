"""
CORRECAO_COMPLETA.py — Dedup automatico de pacientes
============================================================
1. Normaliza CPF/CNS (remove espacos, pontos, tracos)
2. Agrupa por NOME+DTNASC → mescla em 1 paciente
3. Agrupa por CPF → mescla em 1 paciente
4. Agrupa por CNS → mescla em 1 paciente
5. Atendimentos sao migrados para o registro mantido

Nao pede confirmacao — executa direto e mostra resumo.
"""

import sqlite3
import re
import os

SQLITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hospital.db')

LIMPAR_NUM = re.compile(r'\D')


def limpar_numero(valor):
    return LIMPAR_NUM.sub('', str(valor)) if valor else ''


def campos_preenchidos(row):
    """Conta quantos campos NAO vazios o registro tem."""
    return sum(1 for v in row if v and str(v).strip())


def merge_group(grupo, cursor, grupo_nome):
    """
    Recebe lista de rowids que representam a mesma pessoa.
    Mantem o registro com mais dados, migra atendimentos, deleta os outros.
    Retorna (mantido, deletados).
    """
    if len(grupo) < 2:
        return 0, 0

    # Busca dados completos de cada um
    placeholders = ','.join('?' for _ in grupo)
    cursor.execute(f"""
        SELECT rowid, CNS, NUM_CPF, NOME, DTNASC, SEXO, RACA, MAEPCN,
               LOGPCN, NUMPCN, BAIRRO_PCNTE, CEPPCN, IBGE, ETNIA,
               NACIONALIDADE, NOME_SOCIAL, IDADE, ESTADO_CIVIL,
               OCUPACAO, RESPONSAVEL, TELEFONE, CIDADE, ESTADO
        FROM pacientes WHERE rowid IN ({placeholders})
    """, grupo)
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]

    # Escolhe o melhor (mais campos preenchidos, menor rowid como desempate)
    rows.sort(key=lambda r: (-campos_preenchidos(r[1:]), r[0]))
    manter = rows[0]
    manter_id = manter[0]

    # Converte para dict
    manter_dict = dict(zip(cols, manter))

    deletados = 0
    for r in rows[1:]:
        r_id = r[0]
        r_dict = dict(zip(cols, r))

        # Junta dados: se o mantido tem vazio, copia do secundario
        updates = []
        for col in cols[1:]:  # pula rowid
            if col in ('CNS', 'NUM_CPF'):
                continue  # tratado separado
            if (not manter_dict.get(col) or str(manter_dict[col]).strip() == '') and r_dict.get(col):
                updates.append(f"[{col}] = ?")
                cursor.execute(f"UPDATE pacientes SET [{col}] = ? WHERE rowid = ?", (r_dict[col], manter_id))

        # CNS: prefere o que tem 15 digitos
        cns_manter = limpar_numero(manter_dict.get('CNS'))
        cns_r = limpar_numero(r_dict.get('CNS'))
        if cns_r and (not cns_manter or len(cns_manter) != 15) and len(cns_r) == 15:
            cursor.execute("UPDATE pacientes SET [CNS] = ? WHERE rowid = ?", (cns_r, manter_id))

        # NUM_CPF: prefere o que tem 11 digitos
        cpf_manter = limpar_numero(manter_dict.get('NUM_CPF'))
        cpf_r = limpar_numero(r_dict.get('NUM_CPF'))
        if cpf_r and (not cpf_manter or len(cpf_manter) != 11) and len(cpf_r) == 11:
            cursor.execute("UPDATE pacientes SET [NUM_CPF] = ? WHERE rowid = ?", (cpf_r, manter_id))

        # Migra atendimentos: relink pelo rowid que vai ser deletado
        # Primeiro descobre qual CPF/CNS o registro deletado usava nos atendimentos
        cpf_old = r_dict.get('NUM_CPF') or ''
        cns_old = r_dict.get('CNS') or ''
        cpf_new = manter_dict.get('NUM_CPF') or ''
        cns_new = manter_dict.get('CNS') or ''

        if cpf_old and cpf_new and limpar_numero(cpf_old) != limpar_numero(cpf_new):
            cursor.execute("UPDATE atendimentos SET cpf = ? WHERE cpf = ?", (cpf_new, cpf_old))
        if cns_old and cns_new and limpar_numero(cns_old) != limpar_numero(cns_new):
            cursor.execute("UPDATE atendimentos SET sus = ? WHERE sus = ?", (cns_new, cns_old))

        # Deleta o secundario
        cursor.execute("DELETE FROM pacientes WHERE rowid = ?", (r_id,))
        deletados += 1

    return 1, deletados


def main():
    sq = sqlite3.connect(SQLITE)
    sq.row_factory = sqlite3.Row
    csq = sq.cursor()

    total_inicial = csq.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    print(f"Total pacientes antes: {total_inicial}\n")

    # ===================================================================
    # FASE 0: Normalizar CPF/CNS (remover formatacao)
    # ===================================================================
    print("=" * 60)
    print("FASE 0: Normalizando CPF/CNS (removendo formatacao)...")
    print("=" * 60)

    csq.execute("SELECT rowid, CNS, NUM_CPF FROM pacientes")
    norm_cns = norm_cpf = 0
    for r in csq.fetchall():
        cns_old = r['CNS']
        cpf_old = r['NUM_CPF']
        cns_new = limpar_numero(cns_old) if cns_old else ''
        cpf_new = limpar_numero(cpf_old) if cpf_old else ''
        if cns_new != (cns_old or ''):
            csq.execute("UPDATE pacientes SET [CNS] = ? WHERE rowid = ?", (cns_new, r['rowid']))
            norm_cns += 1
        if cpf_new != (cpf_old or ''):
            csq.execute("UPDATE pacientes SET [NUM_CPF] = ? WHERE rowid = ?", (cpf_new, r['rowid']))
            norm_cpf += 1
    sq.commit()
    print(f"  CNS normalizados: {norm_cns}")
    print(f"  CPF normalizados: {norm_cpf}\n")

    total_removidos = 0
    total_mantidos = 0

    # ===================================================================
    # FASE 0.5: Validar CPF/CNS — limpar invalidos, deletar sem nenhum
    # ===================================================================
    print("=" * 60)
    print("FASE 0.5: Validando CPF/CNS...")
    print("=" * 60)

    csq.execute("SELECT rowid, CNS, NUM_CPF, NOME FROM pacientes")
    limpos_cpf = limpos_cns = deletados_sem_doc = 0
    for r in csq.fetchall():
        cns = r['CNS'] or ''
        cpf = r['NUM_CPF'] or ''
        nome = r['NOME'] or ''
        cpf_valido = len(cpf) == 11
        cns_valido = len(cns) == 15

        if cpf and not cpf_valido:
            csq.execute("UPDATE pacientes SET [NUM_CPF] = '' WHERE rowid = ?", (r['rowid'],))
            limpos_cpf += 1
        if cns and not cns_valido:
            csq.execute("UPDATE pacientes SET [CNS] = '' WHERE rowid = ?", (r['rowid'],))
            limpos_cns += 1
        if not cpf_valido and not cns_valido:
            deletados_sem_doc += 1
            csq.execute("DELETE FROM pacientes WHERE rowid = ?", (r['rowid'],))

    sq.commit()
    total_removidos += deletados_sem_doc
    print(f"  CPF invalidos limpos:   {limpos_cpf}")
    print(f"  CNS invalidos limpos:   {limpos_cns}")
    print(f"  Pacientes deletados     {deletados_sem_doc}")
    print(f"  (sem CPF nem CNS validos)\n")

    # ===================================================================
    # FASE 1: Duplicatas por NOME + DTNASC
    # ===================================================================
    print("=" * 60)
    print("FASE 1: Agrupando por NOME + DTNASC...")
    print("=" * 60)

    csq.execute("""
        SELECT rowid FROM pacientes
        WHERE NOME IS NOT NULL AND NOME != ''
          AND DTNASC IS NOT NULL AND DTNASC != ''
        ORDER BY NOME, DTNASC
    """)
    todos = [(r['rowid'],) for r in csq.fetchall()]

    # Agrupa manualmente
    csq.execute("""
        SELECT NOME, DTNASC, COUNT(*) as cnt
        FROM pacientes
        WHERE NOME IS NOT NULL AND NOME != ''
          AND DTNASC IS NOT NULL AND DTNASC != ''
        GROUP BY NOME, DTNASC
        HAVING cnt > 1
    """)
    grupos_nome = csq.fetchall()
    print(f"  Grupos com mesmo NOME+DTNASC: {len(grupos_nome)}")

    mantido = deletados = 0
    for g in grupos_nome:
        csq.execute("SELECT rowid FROM pacientes WHERE NOME = ? AND DTNASC = ? ORDER BY rowid", (g[0], g[1]))
        rowids = [r['rowid'] for r in csq.fetchall()]
        m, d = merge_group(rowids, csq, 'NOME+DTNASC')
        mantido += m
        deletados += d

    sq.commit()
    total_mantidos += mantido
    total_removidos += deletados
    print(f"  Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ===================================================================
    # FASE 2: Duplicatas por CPF
    # ===================================================================
    print("=" * 60)
    print("FASE 2: Agrupando por CPF...")
    print("=" * 60)

    csq.execute("""
        SELECT NUM_CPF, COUNT(*) as cnt
        FROM pacientes
        WHERE NUM_CPF IS NOT NULL AND NUM_CPF != '' AND LENGTH(NUM_CPF) >= 11
        GROUP BY NUM_CPF
        HAVING cnt > 1
    """)
    grupos_cpf = csq.fetchall()
    print(f"  Grupos com mesmo CPF: {len(grupos_cpf)}")

    mantido = deletados = 0
    for g in grupos_cpf:
        csq.execute("SELECT rowid FROM pacientes WHERE NUM_CPF = ? ORDER BY rowid", (g[0],))
        rowids = [r['rowid'] for r in csq.fetchall()]
        m, d = merge_group(rowids, csq, 'CPF')
        mantido += m
        deletados += d

    sq.commit()
    total_mantidos += mantido
    total_removidos += deletados
    print(f"  Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ===================================================================
    # FASE 3: Duplicatas por CNS
    # ===================================================================
    print("=" * 60)
    print("FASE 3: Agrupando por CNS...")
    print("=" * 60)

    csq.execute("""
        SELECT CNS, COUNT(*) as cnt
        FROM pacientes
        WHERE CNS IS NOT NULL AND CNS != '' AND LENGTH(CNS) >= 15
        GROUP BY CNS
        HAVING cnt > 1
    """)
    grupos_cns = csq.fetchall()
    print(f"  Grupos com mesmo CNS: {len(grupos_cns)}")

    mantido = deletados = 0
    for g in grupos_cns:
        csq.execute("SELECT rowid FROM pacientes WHERE CNS = ? ORDER BY rowid", (g[0],))
        rowids = [r['rowid'] for r in csq.fetchall()]
        m, d = merge_group(rowids, csq, 'CNS')
        mantido += m
        deletados += d

    sq.commit()
    total_mantidos += mantido
    total_removidos += deletados
    print(f"  Mantidos: {mantido}  |  Removidos: {deletados}\n")

    # ===================================================================
    # RESUMO FINAL
    # ===================================================================
    total_final = csq.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]

    print("=" * 60)
    print("  RESUMO DA CORRECAO")
    print("=" * 60)
    print(f"  Pacientes antes:          {total_inicial}")
    print(f"  Pacientes removidos:      {total_removidos}")
    print(f"  Pacientes mantidos:       {total_mantidos}")
    print(f"  Pacientes depois:         {total_final}")
    diff = total_inicial - total_final
    print(f"  Diferenca:                {diff}")
    print("=" * 60)

    # Verifica se ainda restam duplicatas
    csq.execute("""
        SELECT COUNT(*) FROM (
            SELECT NUM_CPF FROM pacientes
            WHERE NUM_CPF IS NOT NULL AND NUM_CPF != '' AND LENGTH(NUM_CPF) >= 11
            GROUP BY NUM_CPF HAVING COUNT(*) > 1
        )
    """)
    restam_cpf = csq.fetchone()[0]
    csq.execute("""
        SELECT COUNT(*) FROM (
            SELECT CNS FROM pacientes
            WHERE CNS IS NOT NULL AND CNS != '' AND LENGTH(CNS) >= 15
            GROUP BY CNS HAVING COUNT(*) > 1
        )
    """)
    restam_cns = csq.fetchone()[0]
    csq.execute("""
        SELECT COUNT(*) FROM (
            SELECT NOME, DTNASC FROM pacientes
            WHERE NOME IS NOT NULL AND NOME != ''
              AND DTNASC IS NOT NULL AND DTNASC != ''
            GROUP BY NOME, DTNASC HAVING COUNT(*) > 1
        )
    """)
    restam_nome = csq.fetchone()[0]

    if restam_cpf or restam_cns or restam_nome:
        print(f"\n  ATENCAO: ainda restam duplicatas!")
        print(f"    Por CPF: {restam_cpf}")
        print(f"    Por CNS: {restam_cns}")
        print(f"    Por NOME+DT: {restam_nome}")
    else:
        print("\n  Nenhuma duplicata restante. Banco limpo!")

    sq.close()
    print()


if __name__ == '__main__':
    main()
