"""
04_postgresql_para_firebird.py — Migracao: PostgreSQL (pacientes) -> Firebird (CADCNS)
========================================================================================
Versao atualizada do 03_migrar_pacientes.py que le do novo banco PostgreSQL
em vez do SQLite legado.

REGRAS (identicas ao script anterior):
  - Gera ID_CADCNS = MAX(ID_CADCNS) + 1 para cada insert
  - Valores fixos: CO_LOGRAD='081', CEPPCN='59575000', IBGE='240360'
  - Nulos tratados: LOGPCN='PRINCIPAL', NUMPCN='S/N', BAIRRO_PCNTE='CENTRO'
  - Sexo invalido (nem M nem F) -> 'I'
  - Duplicidade: se CNS ou NUM_CPF ja existir no Firebird, pula o registro
  - Commit a cada 50 registros para evitar lock de banco

DIFERENCAS em relacao ao 03_migrar_pacientes.py:
  - Fonte: PostgreSQL (psycopg2) em vez de SQLite
  - Telefone ja vem separado (ddtel_pcnte + tel_pcnte) — sem precisar extrair DDD
  - ETNIA nao existe no PostgreSQL — enviado como string vazia
  - Colunas do PG sao em minusculo; Firebird em maiusculo
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
        if os.path.exists(_p):
            load_dotenv(_p)
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

# Colunas do Firebird CADCNS para INSERT
COLUNAS_FB_INSERT = [
    'ID_CADCNS',
    'CNS', 'NUM_CPF', 'NOME', 'DTNASC', 'SEXO', 'RACA', 'MAEPCN',
    'LOGPCN', 'NUMPCN', 'BAIRRO_PCNTE', 'CEPPCN', 'IBGE',
    'CO_LOGRAD',
    'ETNIA', 'NACIONALIDADE',
    'DDTEL_PCNTE', 'TEL_PCNTE',
]

# ── FUNCOES AUXILIARES ────────────────────────────────────────────────────────

def limpar_numero(valor):
    if not valor:
        return ''
    return re.sub(r'\D', '', str(valor))


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


def paciente_existe(fb_cur, cns, cpf):
    if cns:
        fb_cur.execute("SELECT 1 FROM CADCNS WHERE CNS = ?", (cns,))
        if fb_cur.fetchone():
            return True
    if cpf:
        fb_cur.execute("SELECT 1 FROM CADCNS WHERE NUM_CPF = ?", (cpf,))
        if fb_cur.fetchone():
            return True
    return False


# ── INICIO ────────────────────────────────────────────────────────────────────

print("=" * 60)
print("  MIGRACAO: PostgreSQL -> Firebird (CADCNS)")
print("=" * 60)

# ── CONEXAO POSTGRESQL ────────────────────────────────────────────────────────

try:
    pg_con = psycopg2.connect(**POSTGRES_CONFIG)
    pg_cur = pg_con.cursor()
    print(f"Conectado ao PostgreSQL ({POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']})")
except Exception as e:
    print(f"ERRO ao conectar no PostgreSQL: {e}")
    sys.exit(1)

pg_cur.execute("SELECT COUNT(*) FROM pacientes")
total_pg = pg_cur.fetchone()[0]
print(f"Total de pacientes no PostgreSQL: {total_pg}")

pg_cur.execute("""
    SELECT
        cns, num_cpf, nome, dtnasc, sexo, raca, maepcn,
        logpcn, numpcn, bairro_pcnte, ceppcn, ibge,
        nacionalidade, ddtel_pcnte, tel_pcnte
    FROM pacientes
    ORDER BY id
""")
rows = pg_cur.fetchall()

# ── CONEXAO FIREBIRD ─────────────────────────────────────────────────────────

try:
    fb_con = firebirdsql.connect(**FIREBIRD_CONFIG)
    fb_cur = fb_con.cursor()
    print("Conectado ao Firebird BPAMAG.GDB com sucesso.\n")
except Exception as e:
    print(f"ERRO ao conectar no Firebird: {e}")
    pg_con.close()
    sys.exit(1)

# ── DESCOBRE O MAIOR ID_CADCNS EXISTENTE ─────────────────────────────────────

try:
    fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
    max_id = fb_cur.fetchone()[0]
    novo_id = max_id if max_id is not None else 0
    print(f"Maior ID_CADCNS no Firebird: {max_id}  |  Proximo ID: {novo_id + 1}")
except Exception as e:
    print(f"ERRO ao consultar MAX(ID_CADCNS): {e}")
    fb_con.close()
    pg_con.close()
    sys.exit(1)

# ── CONTADORES ────────────────────────────────────────────────────────────────

inseridos = 0
pular_duplicata = 0
pular_sem_cns_cpf = 0
sem_nome = 0
erros = 0
processados = 0

placeholders = ', '.join(['?'] * len(COLUNAS_FB_INSERT))
cols = ', '.join(COLUNAS_FB_INSERT)
sql_insert = f"INSERT INTO CADCNS ({cols}) VALUES ({placeholders})"

# ── LOOP PRINCIPAL ────────────────────────────────────────────────────────────

for row in rows:
    cns_raw, cpf_raw, nome_raw, dn_raw, sexo_raw, raca_raw, mae_raw, \
        log_raw, num_raw, bairro_raw, cep_raw, ibge_raw, \
        nac_raw, ddd_raw, tel_raw = row

    cns = limpar_numero(cns_raw)
    cpf = limpar_numero(cpf_raw)

    if not cns and not cpf:
        pular_sem_cns_cpf += 1
        continue

    nome = validar_texto(nome_raw, 30)
    if not nome:
        sem_nome += 1
        continue

    logradouro = validar_texto(log_raw, 30) or 'PRINCIPAL'
    numero     = validar_texto(num_raw, 5)  or 'S/N'
    bairro     = validar_texto(bairro_raw, 30) or 'CENTRO'
    sexo       = validar_sexo(sexo_raw)
    dtnasc     = validar_dtnasc(dn_raw)
    mae        = validar_texto(mae_raw, 30)
    nac        = validar_texto(nac_raw, 3)
    ddd        = validar_texto(ddd_raw, 2)
    tel        = validar_texto(tel_raw, 11)

    # RACA: PostgreSQL ja guarda como '01'-'05'; fallback '03' (Parda)
    raca = validar_texto(raca_raw, 2) or '03'

    try:
        if paciente_existe(fb_cur, cns, cpf):
            pular_duplicata += 1
            processados += 1
            if processados % LOTE == 0:
                fb_con.commit()
            continue
    except Exception as e:
        fb_con.rollback()
        print(f"ERRO ao verificar duplicidade CNS={cns} CPF={cpf}: {e}")
        erros += 1
        continue

    novo_id += 1

    valores = [
        novo_id,
        cns,
        cpf,
        nome,
        dtnasc,
        sexo,
        raca,
        mae,
        logradouro,
        numero,
        bairro,
        '59575000',
        '240360',
        '081',
        '',          # ETNIA — nao existe no PostgreSQL
        nac,
        ddd,
        tel,
    ]

    try:
        fb_cur.execute(sql_insert, valores)
        inseridos += 1
    except Exception as e:
        fb_con.rollback()
        print(f"ERRO ao inserir CNS={cns} CPF={cpf}: {e}")
        erros += 1
        continue

    processados += 1

    if processados % LOTE == 0:
        try:
            fb_con.commit()
            print(f"  [{processados}/{total_pg}] "
                  f"inseridos={inseridos}  duplicatas={pular_duplicata}  erros={erros}")
        except Exception as e:
            print(f"ERRO no commit do lote: {e}")
            fb_con.rollback()

# ── Commit final ──────────────────────────────────────────────────────────────

try:
    fb_con.commit()
except Exception as e:
    print(f"ERRO no commit final: {e}")

# ── RELATORIO FINAL ───────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("        RELATORIO DA MIGRACAO")
print("=" * 60)
print(f"  Total lido do PostgreSQL:   {total_pg}")
print(f"  Inseridos no Firebird:      {inseridos}")
print(f"  Pulados (duplicata):        {pular_duplicata}")
print(f"  Sem CNS/CPF:                {pular_sem_cns_cpf}")
print(f"  Sem nome:                   {sem_nome}")
print(f"  Erros:                      {erros}")
print("=" * 60)

# ── VERIFICACAO POS-MIGRACAO ─────────────────────────────────────────────────

print("\n--- Verificacao pos-migracao ---")
try:
    fb_cur.execute("SELECT COUNT(*) FROM CADCNS")
    print(f"  Total CADCNS no Firebird:   {fb_cur.fetchone()[0]}")

    fb_cur.execute("""
        SELECT
            COUNT(CASE WHEN LOGPCN IS NULL OR LOGPCN = '' THEN 1 END),
            COUNT(CASE WHEN NUMPCN IS NULL OR NUMPCN = '' THEN 1 END),
            COUNT(CASE WHEN BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = '' THEN 1 END),
            COUNT(CASE WHEN CO_LOGRAD IS NULL OR CO_LOGRAD = '' THEN 1 END),
            COUNT(CASE WHEN SEXO NOT IN ('M', 'F') THEN 1 END)
        FROM CADCNS
    """)
    r = fb_cur.fetchone()
    print(f"  Endereco vazio (LOGPCN):    {r[0]}")
    print(f"  Numero vazio (NUMPCN):      {r[1]}")
    print(f"  Bairro vazio:               {r[2]}")
    print(f"  CO_LOGRAD vazio:            {r[3]}")
    print(f"  Sexo invalido:              {r[4]}")

    if r[4] > 0:
        fb_cur.execute("UPDATE CADCNS SET SEXO = 'I' WHERE SEXO NOT IN ('M', 'F')")
        fb_con.commit()
        print(f"  >> Corrigido SEXO invalido em {r[4]} registro(s)")
except Exception as e:
    print(f"  Erro na verificacao: {e}")

# ── FECHANDO CONEXOES ─────────────────────────────────────────────────────────

for con in (fb_con, pg_con):
    try:
        con.close()
    except Exception:
        pass

print("\nMigracao concluida!")
print("=" * 60)
