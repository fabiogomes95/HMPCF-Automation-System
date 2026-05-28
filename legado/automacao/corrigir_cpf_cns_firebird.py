"""
CORRIGIR_CPF_CNS_FIREBIRD.py — Valida CPF/CNS com algoritmos oficiais
======================================================================
- Valida CPF (11 digitos, digito verificador oficial)
- Valida CNS (15 digitos, digito verificador oficial)
- Se CPF invalido e CNS valido: limpa CPF, mantem registro
- Se CNS invalido e CPF valido: limpa CNS, mantem registro
- Se ambos invalidos: remove registro completamente
- Retorna estatisticas completas
"""

import firebirdsql
import re
import os
from datetime import datetime

FB = dict(
    host='localhost',
    database=r'C:\BPA\BPAMAG.GDB',
    user='SYSDBA',
    password='masterkey',
    charset='WIN1252'
)


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


def limpar_numero(valor):
    return re.sub(r'\D', '', str(valor)) if valor else ''


def main():
    con = firebirdsql.connect(**FB)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM CADCNS")
    total_inicial = cur.fetchone()[0]
    print(f"Total CADCNS antes: {total_inicial}")
    print()

    # Buscar todos os registros
    cur.execute("SELECT ID_CADCNS, CNS, NUM_CPF, NOME FROM CADCNS ORDER BY ID_CADCNS")
    registros = cur.fetchall()

    stats = {
        'cpf_invalido_limpo': 0,
        'cns_invalido_limpo': 0,
        'ambos_invalidos_removido': 0,
        'cpf_valido_mantido': 0,
        'cns_valido_mantido': 0,
        'cpf_ok_cns_ok': 0,
    }

    # Collect per-patient details
    detalhes = []

    for r in registros:
        id_cad = r[0]
        cns_raw = (r[1] or '').strip()
        cpf_raw = (r[2] or '').strip()
        nome = (r[3] or '').strip()

        cns_limpo = limpar_numero(cns_raw)
        cpf_limpo = limpar_numero(cpf_raw)

        cns_valido = valida_cns(cns_limpo)
        cpf_valido = valida_cpf(cpf_limpo)

        status = []

        if cpf_raw and not cpf_valido:
            cur.execute("UPDATE CADCNS SET NUM_CPF = '' WHERE ID_CADCNS = ?", (id_cad,))
            stats['cpf_invalido_limpo'] += 1
            status.append(f"CPF {cpf_limpo} INVALIDO -> limpo")

        if cns_raw and not cns_valido:
            cur.execute("UPDATE CADCNS SET CNS = '' WHERE ID_CADCNS = ?", (id_cad,))
            stats['cns_invalido_limpo'] += 1
            status.append(f"CNS {cns_limpo} INVALIDO -> limpo")

        if not cpf_valido and not cns_valido:
            cur.execute("DELETE FROM CADCNS WHERE ID_CADCNS = ?", (id_cad,))
            stats['ambos_invalidos_removido'] += 1
            status.append("AMBOS INVALIDOS -> REMOVIDO")
        elif cpf_valido:
            stats['cpf_valido_mantido'] += 1
            if cns_valido:
                stats['cns_valido_mantido'] += 1
                stats['cpf_ok_cns_ok'] += 1
            status.append(f"CPF {cpf_limpo} OK, mantido")
        elif cns_valido:
            stats['cns_valido_mantido'] += 1
            status.append(f"CNS {cns_limpo} OK, mantido")

        if status:
            detalhes.append(f"  ID {id_cad}: {nome} | {'; '.join(status)}")

    con.commit()

    cur.execute("SELECT COUNT(*) FROM CADCNS")
    total_final = cur.fetchone()[0]

    print("=" * 60)
    print("  RESULTADO DA VALIDACAO CPF/CNS (ALGORITMO OFICIAL)")
    print("=" * 60)
    print(f"  Total CADCNS inicial:                   {total_inicial}")
    print(f"  Total CADCNS final:                     {total_final}")
    print(f"  Removidos (ambos invalidos):             {stats['ambos_invalidos_removido']}")
    print(f"  CPF invalido limpo:                      {stats['cpf_invalido_limpo']}")
    print(f"  CNS invalido limpo:                      {stats['cns_invalido_limpo']}")
    print(f"  Com CPF valido mantido:                  {stats['cpf_valido_mantido']}")
    print(f"  Com CNS valido mantido:                  {stats['cns_valido_mantido']}")
    print(f"  Com ambos validos:                       {stats['cpf_ok_cns_ok']}")
    print(f"  Diferenca (removidos):                   {total_inicial - total_final}")
    print("=" * 60)

    if detalhes:
        print(f"\nDetalhamento dos {len(detalhes)} registros alterados/removidos:")
        for d in detalhes:
            print(d)

    con.close()
    return stats, total_inicial, total_final


if __name__ == '__main__':
    main()
