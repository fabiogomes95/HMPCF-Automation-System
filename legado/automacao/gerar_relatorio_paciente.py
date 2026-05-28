"""
GERAR_RELATORIO_PACIENTE.py — Gera PDF profissional de um paciente
====================================================================
Uso: python gerar_relatorio_paciente.py

- Busca por nome, CPF ou CNS em ambos os bancos (SQLite e Firebird)
- Mostra todas as variacoes de nome/CPF/CNS do mesmo paciente
- Gera PDF profissional no formato de cards (como o relatorio da CLEONI)
- Usa fpdf2 (instalar com: pip install fpdf2)
"""

import os
import re
import sys
import sqlite3
import firebirdsql
from datetime import datetime
from fpdf import FPDF, XPos, YPos
from collections import defaultdict

SQLITE = r'C:\Users\User\Documents\HMPCF-Automation-System\hospital.db'
FB = dict(host='localhost', database=r'C:\BPA\BPAMAG.GDB', user='SYSDBA', password='masterkey', charset='WIN1252')
PASTA = os.path.dirname(os.path.abspath(__file__))

MESES = {
    1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARCO', 4: 'ABRIL',
    5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
    9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
}


def limpar_numero(v):
    return re.sub(r'\D', '', str(v)) if v else ''


def formatar_cpf(cpf):
    d = limpar_numero(cpf)
    if len(d) == 11:
        return f'{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}'
    return cpf


def formatar_cns(cns):
    d = limpar_numero(cns)
    if len(d) == 15:
        return f'{d[:3]} {d[3:7]} {d[7:11]} {d[11:]}'
    return cns


def formatar_data(data_str):
    if not data_str:
        return '(sem data)'
    try:
        if '-' in str(data_str):
            return datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        pass
    return str(data_str)


# ===================================================================
# ENTRADA DO USUARIO
# ===================================================================

print("=" * 60)
print("  GERAR RELATORIO DE PACIENTE")
print("=" * 60)
if len(sys.argv) > 1:
    termo = sys.argv[1].strip()
else:
    termo = input("Digite nome, CPF ou CNS do paciente: ").strip()
if not termo:
    print("Nada digitado. Saindo.")
    exit()

termo_clean = limpar_numero(termo)
print()

# ===================================================================
# BUSCA NO SQLITE
# ===================================================================

sq = sqlite3.connect(SQLITE)
sq.row_factory = sqlite3.Row
csq = sq.cursor()

if termo_clean and len(termo_clean) >= 11:
    if len(termo_clean) == 15:
        csq.execute("SELECT * FROM pacientes WHERE CNS LIKE ?", (f'%{termo_clean}%',))
    else:
        csq.execute("SELECT * FROM pacientes WHERE NUM_CPF LIKE ?", (f'%{termo_clean}%',))
else:
    csq.execute("SELECT * FROM pacientes WHERE NOME LIKE ?", (f'%{termo.upper()}%',))

resultados_sq = csq.fetchall()

if not resultados_sq:
    print("Nenhum paciente encontrado no SQLite.")
    sq.close()
    exit()

print(f"Encontrados {len(resultados_sq)} registro(s) no SQLite (pacientes):")
for r in resultados_sq:
    nome = r['NOME'] or '(sem nome)'
    cpf = formatar_cpf(r['NUM_CPF']) if r['NUM_CPF'] else '(vazio)'
    cns = formatar_cns(r['CNS']) if r['CNS'] else '(vazio)'
    dt = r['DTNASC'] or '(sem data)'
    print(f"  CNS={cns:21s} | CPF={cpf:16s} | {nome:40s} | NASC={dt}")

# ===================================================================
# AGRUPA POR CPF — encontra todas as variacoes do mesmo paciente
# ===================================================================

print()
print("=" * 60)
print("  VARIACOES ENCONTRADAS (MESMO CPF)")
print("=" * 60)

cpf_principal = None
cpf_count = defaultdict(list)

for r in resultados_sq:
    cpf_c = limpar_numero(r['NUM_CPF'])
    if cpf_c:
        cpf_count[cpf_c].append(r)
    else:
        # sem CPF, agrupa pelo CNS
        cns_c = limpar_numero(r['CNS'])
        if cns_c:
            cpf_count[cns_c].append(r)

# Se CPF passado como argumento, usa direto
if len(sys.argv) > 2:
    cpf_principal = limpar_numero(sys.argv[2])
    print(f"  CPF/CNS da linha de comando: {cpf_principal}")
elif len(cpf_count) == 1 and len(resultados_sq) == 1:
    # Caso simples: 1 registro, 1 CPF
    cpf_principal = limpar_numero(resultados_sq[0]['NUM_CPF']) or limpar_numero(resultados_sq[0]['CNS'])
    print("  Apenas 1 registro encontrado.")
    print(f"  CPF principal: {formatar_cpf(cpf_principal)}")
else:
    # Mostra os grupos
    grupos = list(cpf_count.items())
    if len(grupos) == 1:
        cpf_principal = grupos[0][0]
        print(f"  CPF unico: {formatar_cpf(cpf_principal)}")
        for r in grupos[0][1]:
            nome = r['NOME'] or '(sem nome)'
            print(f"    - {nome:40s} | CNS={r['CNS'] or '(vazio)'}")
    else:
        print("  Multiplos CPF/CNS encontrados para este nome:")
        for i, (chave, regs) in enumerate(grupos, 1):
            cpf_str = formatar_cpf(chave) if len(chave) == 11 else formatar_cns(chave)
            chave_cpf = chave if len(chave) == 11 else ''
            chave_cns = chave if len(chave) == 15 else ''
            atds = buscar_atendimentos(chave_cpf, chave_cns)
            total_atend = len(atds)
            print(f"  {i}. {cpf_str} — {len(regs)} registro(s), {total_atend} atendimento(s)")
            for r in regs:
                nome = r['NOME'] or '(sem nome)'
                print(f"       {nome:40s} | CNS={r['CNS'] or '(vazio)':20s} | DTNASC={r['DTNASC'] or ''}")

        resp = input("\nQual CPF/CNS usar como principal? (Digite o numero ou ENTER para o 1): ").strip()
        if resp:
            cpf_principal = limpar_numero(resp)
        else:
            cpf_principal = grupos[0][0]

if not cpf_principal:
    print("CPF/CNS nao definido. Saindo.")
    sq.close()
    exit()

# ===================================================================
# BUSCA TODOS OS ATENDIMENTOS DESTE CPF/CNS
# ===================================================================

print()
print("=" * 60)
print("  BUSCANDO ATENDIMENTOS...")
print("=" * 60)

def buscar_atendimentos(cpf, cns):
    """Busca atendimentos pelo CPF e CNS, nas variacoes com e sem formatacao."""
    resultados = []

    if cpf:
        cpf_fmt = f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}' if len(cpf) == 11 else cpf
        csq.execute("SELECT DISTINCT data_atendimento, hora_atendimento FROM atendimentos WHERE cpf IN (?, ?) ORDER BY data_atendimento, hora_atendimento", (cpf, cpf_fmt))
        resultados.extend(csq.fetchall())

    if cns:
        cns_fmt = f'{cns[:3]} {cns[3:7]} {cns[7:11]} {cns[11:]}' if len(cns) == 15 else cns
        csq.execute("SELECT DISTINCT data_atendimento, hora_atendimento FROM atendimentos WHERE sus IN (?, ?) ORDER BY data_atendimento, hora_atendimento", (cns, cns_fmt))
        resultados.extend(csq.fetchall())

    # Remove duplicatas (mesma data+hora)
    vistos = set()
    unicos = []
    for data, hora in resultados:
        chave = (data, hora)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append((data, hora))
    return unicos


atendimentos = []
if len(cpf_principal) == 11:
    atendimentos = buscar_atendimentos(cpf_principal, '')
elif len(cpf_principal) == 15:
    atendimentos = buscar_atendimentos('', cpf_principal)

if not atendimentos:
    # Tenta achar por CNS das variacoes
    cnss = set()
    for r in resultados_sq:
        c = limpar_numero(r['CNS'])
        if c:
            cnss.add(c)
    for cns in cnss:
        atendimentos.extend(buscar_atendimentos('', cns))

# Busca todas as variacoes de nome no SQLite para este CPF
csq.execute("SELECT DISTINCT NOME, NUM_CPF, CNS, DTNASC, SEXO, LOGPCN, NUMPCN, BAIRRO_PCNTE FROM pacientes WHERE NUM_CPF LIKE ? OR CNS IN (SELECT CNS FROM pacientes WHERE NUM_CPF LIKE ?)", (f'%{cpf_principal}%', f'%{cpf_principal}%'))
variacoes_nome = csq.fetchall()

print(f"  Total de atendimentos encontrados: {len(atendimentos)}")
print(f"  Variacoes de nome/CPF no cadastro: {len(variacoes_nome)}")

# ===================================================================
# AGRUPA POR MES
# ===================================================================

meses = defaultdict(list)
for data, hora in atendimentos:
    mes_chave = '00'
    if data:
        try:
            if '-' in str(data):
                dt = datetime.strptime(data, '%Y-%m-%d')
                mes_chave = f'{dt.year}-{dt.month:02d}'
            else:
                mes_chave = f'XXXX-{data[:2]}' if len(data) >= 2 else '00'
        except ValueError:
            mes_chave = '00'
    entrada = f'{hora} - {formatar_data(data)}' if hora else f'{formatar_data(data)}'
    meses[mes_chave].append(entrada)

# Ordena por mes
meses_ordenados = sorted(meses.items(), key=lambda x: x[0])

# ===================================================================
# GERA PDF
# ===================================================================

print()
print("=" * 60)
print("  GERANDO PDF...")
print("=" * 60)

# Nome para o arquivo
nome_arquivo = limpar_numero(cpf_principal)
if not nome_arquivo:
    nome_arquivo = 'paciente'
arquivo_pdf = os.path.join(PASTA, f'relatorio_{nome_arquivo}.pdf')

pdf = FPDF(orientation='P', unit='mm', format='A4')
pdf.set_auto_page_break(auto=False)
pdf.add_page()

LARGURA_COL = 88
MARGEM_ESQ = 10
ENTRE_COL = 8
MARGEM_INFERIOR = 20
coluna_x = [MARGEM_ESQ, MARGEM_ESQ + LARGURA_COL + ENTRE_COL]


def cabecalho():
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'HMPCF - RELATORIO DE PACIENTE', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(3)

    # Dados principais do paciente
    primeiro_nome = variacoes_nome[0][0] if variacoes_nome and variacoes_nome[0][0] else '(sem nome)'
    primeira_dt = variacoes_nome[0][3] if variacoes_nome else ''
    primeiro_cpf = variacoes_nome[0][1] if variacoes_nome else cpf_principal
    primeiro_cns = variacoes_nome[0][2] if variacoes_nome else ''

    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 6, primeiro_nome, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, f'CPF: {formatar_cpf(primeiro_cpf)}  |  CNS: {formatar_cns(primeiro_cns)}  |  NASC: {primeira_dt}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # Variacoes de nome
    if len(variacoes_nome) > 1:
        pdf.set_font('Helvetica', 'I', 7)
        pdf.cell(0, 3, 'Variacoes encontradas no cadastro:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for v in variacoes_nome:
            vnome = v[0] or '(sem nome)'
            vcpf = formatar_cpf(v[1]) if v[1] else '(vazio)'
            vcns = formatar_cns(v[2]) if v[2] else '(vazio)'
            pdf.cell(0, 3, f'  NOME={vnome}  CPF={vcpf}  CNS={vcns}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 5, f'TOTAL DE ATENDIMENTOS: {len(atendimentos)}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


cabecalho()

col = 0
y = pdf.get_y()


cabecalho_y = pdf.get_y()
y = cabecalho_y
col = 0


def coluna_atual(col, y):
    if y > 297 - MARGEM_INFERIOR:
        col += 1
        if col > 1:
            pdf.add_page()
            col = 0
            y = 25
        else:
            y = 25
    return col, y

for mes_chave, entradas in meses_ordenados:
    # Nome do mes
    try:
        ano_mes = mes_chave.split('-')
        ano = ano_mes[0]
        mes_num = int(ano_mes[1])
        titulo_mes = f'{MESES[mes_num]} ({len(entradas)})' if ano == 'XXXX' else f'{MESES[mes_num]}/{ano} ({len(entradas)})'
    except (IndexError, ValueError):
        titulo_mes = f'DESCONHECIDO ({len(entradas)})'

    # Calcula altura do card do mes
    alt_card = 10 + len(entradas) * 4.5

    # Verifica se cabe na coluna atual
    col, y = coluna_atual(col, y)
    x0 = coluna_x[col]

    if y + alt_card > 297 - MARGEM_INFERIOR:
        col += 1
        if col > 1:
            pdf.add_page()
            col = 0
            y = 25
        else:
            y = 25
        x0 = coluna_x[col]

    # Card do mes
    pdf.set_xy(x0, y)
    pdf.set_fill_color(248, 248, 248)
    pdf.set_draw_color(180, 180, 180)
    pdf.rect(x0, y, LARGURA_COL, alt_card)
    pdf.set_xy(x0 + 2, y + 1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(LARGURA_COL - 4, 5, titulo_mes)
    pdf.set_xy(x0 + 2, pdf.get_y() + 0.5)
    pdf.set_font('Helvetica', '', 7)

    for i, entrada in enumerate(entradas, 1):
        pdf.set_x(x0 + 2)
        pdf.cell(LARGURA_COL - 4, 4.5, f'[{i:02d}] {entrada}')

    y = pdf.get_y() + 3

pdf.output(arquivo_pdf)
print(f"  PDF gerado: {arquivo_pdf}")

sq.close()

# ===================================================================
# BUSCA NO FIREBIRD (informativo)
# ===================================================================

print()
print("=" * 60)
print("  INFORMACAO DO FIREBIRD")
print("=" * 60)

try:
    fb = firebirdsql.connect(**FB)
    cfb = fb.cursor()

    chave = cpf_principal
    if len(chave) == 11:
        cfb.execute("SELECT ID_CADCNS, NUM_CPF, CNS, NOME, DTNASC FROM CADCNS WHERE NUM_CPF = ?", (chave,))
    else:
        cfb.execute("SELECT ID_CADCNS, NUM_CPF, CNS, NOME, DTNASC FROM CADCNS WHERE CNS = ?", (chave,))
    rows = cfb.fetchall()
    if rows:
        print(f"  Encontrado(s) no Firebird ({len(rows)} registro(s)):")
        for r in rows:
            print(f"    ID={r[0]} | CPF={r[1] or '(vazio)':16s} | CNS={r[2] or '(vazio)':20s} | {r[3] or '(sem nome)':40s} | NASC={r[4] or ''}")
    else:
        print("  Nao encontrado no Firebird.")
    fb.close()
except Exception as e:
    print(f"  Erro ao conectar no Firebird: {e}")

print()
print("=" * 60)
print("  PRONTO!")
print("=" * 60)
