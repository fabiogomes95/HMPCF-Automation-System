"""
MIGRAR_PACIENTES.py — Migracao definitiva: SQLite (pacientes) -> Firebird (CADCNS)
===================================================================================
Le todos os registros da tabela `pacientes` do SQLite e insere na tabela `CADCNS`
do Firebird (BPAMAG.GDB) respeitando todas as regras de negocio.

REGRAS:
  - Gera manualmente ID_CADCNS (MAX + 1 para cada insert)
  - Valores fixos: CO_LOGRAD='081', CEPPCN='59575000', IBGE='240360'
  - Nulos tratados: LOGPCN='PRINCIPAL', NUMPCN='S/N', BAIRRO_PCNTE='CENTRO'
  - Sexo invalido (nem M nem F) -> 'I'
  - Demais colunas de texto: None -> '' (string vazia)
  - Duplicidade: se CNS ou NUM_CPF ja existir no Firebird, pula o registro
  - Commit a cada 50 registros para evitar lock de banco
"""

import os
import re
import sqlite3
import firebirdsql

# ── CONFIGURACOES ─────────────────────────────────────────────────────────────

SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'hospital.db'
)

FIREBIRD_CONFIG = dict(
    host='localhost',
    database=r'C:\BPA\BPAMAG.GDB',
    user='SYSDBA',
    password='masterkey',
    charset='WIN1252'
)

# Colunas do SQLite que vamos ler (na ordem da tabela pacientes)
COLUNAS_SQLITE = [
    'CNS', 'NUM_CPF', 'NOME', 'DTNASC', 'SEXO', 'RACA', 'MAEPCN',
    'LOGPCN', 'NUMPCN', 'BAIRRO_PCNTE', 'CEPPCN', 'IBGE',
    'ETNIA', 'NACIONALIDADE', 'TELEFONE'
]

# Colunas do Firebird CADCNS para INSERT (ID_CADCNS vai na frente manualmente)
COLUNAS_FB_INSERT = [
    'ID_CADCNS',
    'CNS', 'NUM_CPF', 'NOME', 'DTNASC', 'SEXO', 'RACA', 'MAEPCN',
    'LOGPCN', 'NUMPCN', 'BAIRRO_PCNTE', 'CEPPCN', 'IBGE',
    'CO_LOGRAD',
    'ETNIA', 'NACIONALIDADE',
    'DDTEL_PCNTE', 'TEL_PCNTE'
]

# ── FUNCOES AUXILIARES ────────────────────────────────────────────────────────


def limpar_numero(valor):
    """Remove tudo que nao for digito."""
    if not valor:
        return ''
    return re.sub(r'\D', '', str(valor))


def extrair_ddd_tel(telefone):
    """Extrai DDD (2 digitos) e telefone (resto) de uma string de telefone.
    Ex: '(84) 98806-4635' -> ('84', '988064635')
    """
    digits = limpar_numero(telefone)
    if not digits:
        return ('', '')
    if len(digits) <= 2:
        return (digits, '')
    return (digits[:2], digits[2:])


def validar_dtnasc(valor):
    """Valida data de nascimento, retorna YYYYMMDD ou None."""
    if not valor:
        return None
    v = str(valor).strip().replace('-', '').replace('/', '')
    if len(v) == 8 and v.isdigit():
        return v
    return None


def validar_sexo(valor):
    """Retorna 'M', 'F' ou 'I'."""
    if not valor:
        return 'I'
    s = str(valor).strip().upper()
    return s if s in ('M', 'F') else 'I'


def validar_texto(valor, max_len=9999):
    """Converte para string vazia se None; faz upper e truncamento."""
    if valor is None:
        return ''
    s = str(valor).strip().upper()
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s


def paciente_existe(fb_cur, cns, cpf):
    """Retorna True se CNS ou CPF ja existir no CADCNS."""
    if cns:
        fb_cur.execute("SELECT 1 FROM CADCNS WHERE CNS = ?", (cns,))
        if fb_cur.fetchone():
            return True
    if cpf:
        fb_cur.execute("SELECT 1 FROM CADCNS WHERE NUM_CPF = ?", (cpf,))
        if fb_cur.fetchone():
            return True
    return False


# ── CONEXAO SQLITE ────────────────────────────────────────────────────────────

print("=" * 60)
print("  MIGRAR PACIENTES: SQLite -> Firebird (CADCNS)")
print("=" * 60)

sq_con = sqlite3.connect(SQLITE_PATH)
sq_cur = sq_con.cursor()

sq_cur.execute("SELECT COUNT(*) FROM pacientes")
total_sqlite = sq_cur.fetchone()[0]
print(f"\nTotal de pacientes no SQLite: {total_sqlite}")

cols_sql = ', '.join(COLUNAS_SQLITE)
sq_cur.execute(f"SELECT {cols_sql} FROM pacientes")

# ── CONEXAO FIREBIRD ─────────────────────────────────────────────────────────

try:
    fb_con = firebirdsql.connect(**FIREBIRD_CONFIG)
    fb_cur = fb_con.cursor()
    print("Conectado ao Firebird BPAMAG.GDB com sucesso.\n")
except Exception as e:
    print(f"ERRO ao conectar no Firebird: {e}")
    sq_con.close()
    exit(1)

# ── DESCOBRE O MAIOR ID_CADCNS EXISTENTE ─────────────────────────────────────

try:
    fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
    max_id = fb_cur.fetchone()[0]
    novo_id = max_id if max_id is not None else 0
    print(f"Maior ID_CADCNS encontrado: {max_id}  |  Proximo ID: {novo_id + 1}")
except Exception as e:
    print(f"ERRO ao consultar MAX(ID_CADCNS): {e}")
    fb_con.close()
    sq_con.close()
    exit(1)

# ── CONTADORES ────────────────────────────────────────────────────────────────

inseridos = 0
pular_duplicata = 0
pular_sem_cns_cpf = 0
sem_nome = 0
erros = 0
processados = 0
LOTE = 50

# ── LOOP PRINCIPAL ────────────────────────────────────────────────────────────

for row in sq_cur:
    cns_raw, cpf_raw, nome_raw, dn_raw, sexo_raw, raca_raw, mae_raw, \
        log_raw, num_raw, bairro_raw, cep_raw, ibge_raw, \
        etnia_raw, nac_raw, tel_raw = row

    # ── Limpa CNS e CPF ──
    cns = limpar_numero(cns_raw)
    cpf = limpar_numero(cpf_raw)

    # ── Pula se nao tem CNS nem CPF ──
    if not cns and not cpf:
        pular_sem_cns_cpf += 1
        continue

    # ── Valida nome (obrigatorio) ──
    nome = validar_texto(nome_raw, 30)
    if not nome:
        sem_nome += 1
        continue

    # ── Valida CNS (deve ter 15 digitos) ──
    if cns and len(cns) != 15:
        erros += 1
        print(f"  CNS invalido (tamanho {len(cns)}): {cns}")
        continue

    # ── Valida CPF (deve ter 11 digitos) ──
    if cpf and len(cpf) != 11:
        erros += 1
        print(f"  CPF invalido (tamanho {len(cpf)}): {cpf}")
        continue

    # ── Tratamento de nulos e valores padrao ──
    logradouro = validar_texto(log_raw, 30)
    if not logradouro:
        logradouro = 'PRINCIPAL'

    numero = validar_texto(num_raw, 5)
    if not numero:
        numero = 'S/N'

    bairro = validar_texto(bairro_raw, 30)
    if not bairro:
        bairro = 'CENTRO'

    sexo = validar_sexo(sexo_raw)

    dtnasc = validar_dtnasc(dn_raw)

    # ── Telefone: extrai DDD e numero ──
    ddd, tel = extrair_ddd_tel(tel_raw)

    # ── Demais campos de texto: None vira '' ──
    etnia = validar_texto(etnia_raw, 4)
    nacionalidade = validar_texto(nac_raw, 3)
    mae = validar_texto(mae_raw, 30)

    # ── Verifica duplicidade ──
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

    # ── Prepara INSERT ──
    novo_id += 1

    valores = [
        novo_id,
        cns,
        cpf,
        nome,
        dtnasc,
        sexo,
        '03',               # RACA fixa '03' (Parda)
        mae,
        logradouro,
        numero,
        bairro,
        '59575000',          # CEPPCN fixo
        '240360',            # IBGE fixo (Extremoz)
        '081',               # CO_LOGRAD fixo
        etnia,
        nacionalidade,
        ddd,
        tel
    ]

    placeholders = ', '.join(['?'] * len(COLUNAS_FB_INSERT))
    cols = ', '.join(COLUNAS_FB_INSERT)

    try:
        fb_cur.execute(
            f"INSERT INTO CADCNS ({cols}) VALUES ({placeholders})",
            valores
        )
        inseridos += 1
    except Exception as e:
        fb_con.rollback()
        print(f"ERRO ao inserir CNS={cns} CPF={cpf}: {e}")
        erros += 1
        continue

    processados += 1

    # ── Commit em lotes ──
    if processados % LOTE == 0:
        try:
            fb_con.commit()
            print(f"  [{processados}/{total_sqlite}] processados... "
                  f"(inseridos={inseridos}, erros={erros}, "
                  f"duplicatas={pular_duplicata})")
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
print(f"  Total lido do SQLite:       {total_sqlite}")
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
    total_fb = fb_cur.fetchone()[0]
    print(f"  Total CADCNS no Firebird:   {total_fb}")

    fb_cur.execute("""
        SELECT
            COUNT(CASE WHEN LOGPCN IS NULL OR LOGPCN = '' THEN 1 END) AS sem_log,
            COUNT(CASE WHEN NUMPCN IS NULL OR NUMPCN = '' THEN 1 END) AS sem_num,
            COUNT(CASE WHEN BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = '' THEN 1 END) AS sem_bairro,
            COUNT(CASE WHEN CEPPCN IS NULL OR CEPPCN = '' THEN 1 END) AS sem_cep,
            COUNT(CASE WHEN CO_LOGRAD IS NULL OR CO_LOGRAD = '' THEN 1 END) AS sem_co_lograd,
            COUNT(CASE WHEN SEXO NOT IN ('M', 'F') THEN 1 END) AS sexo_invalido
        FROM CADCNS
    """)
    r = fb_cur.fetchone()
    print(f"  Endereco vazio (LOGPCN):    {r[0]}")
    print(f"  Numero vazio (NUMPCN):      {r[1]}")
    print(f"  Bairro vazio:               {r[2]}")
    print(f"  CEP vazio:                  {r[3]}")
    print(f"  CO_LOGRAD vazio:            {r[4]}")
    print(f"  Sexo invalido:              {r[5]}")

    if r[5] > 0:
        fb_cur.execute("UPDATE CADCNS SET SEXO = 'I' WHERE SEXO NOT IN ('M', 'F')")
        fb_con.commit()
        print(f"  >> Sexo invalido corrigido para 'I' em {r[5]} registro(s)")

except Exception as e:
    print(f"  Erro na verificacao: {e}")

# ── FECHANDO CONEXOES ─────────────────────────────────────────────────────────

try:
    fb_con.close()
except Exception:
    pass

try:
    sq_con.close()
except Exception:
    pass

print("\nMigracao concluida!")
print("=" * 60)
