#!/usr/bin/env python3
"""
migrate_to_postgres.py
======================
Migracao completa: hospital.db (SQLite legado) -> PostgreSQL (HMPCF)

O que este script faz (rode uma unica vez):
  1. Cria as tabelas pacientes e recepcao_atendimentos no PostgreSQL
  2. Migra todos os pacientes com validacao matematica de CPF (mod 11) e CNS (DATASUS)
  3. Migra os atendimentos vinculando pelo CPF/CNS do paciente
  4. Deduplicacao automatica: registros ja existentes no PG sao pulados

Mapeamento de colunas (SQLite antigo -> PostgreSQL):
  cpf         -> num_cpf      (validacao CPF mod 11)
  sus         -> cns          (validacao CNS DATASUS)
  nome        -> nome         (UPPERCASE)
  nomeSocial  -> nome_social
  dn          -> dtnasc       (formato YYYYMMDD)
  sexo        -> sexo         (M / F / I)
  raca        -> raca         (codigos 01-05)
  mae         -> maepcn
  endereco    -> logpcn
  numero      -> numpcn
  bairro      -> bairro_pcnte
  tel         -> ddtel_pcnte + tel_pcnte  (separa DDD do numero)
  idade       -> idade
  civil       -> civil
  ocupacao    -> ocupacao
  responsavel -> responsavel
  cidade      -> cidade
  estado      -> estado
  naturalidade-> nacionalidade

Valores fixos injetados em todos os registros:
  ibge      = '240360'
  ceppcn    = '59575000'
  co_lograd = '081'

USO:
    python migrate_to_postgres.py              # migracao completa
    python migrate_to_postgres.py --dry-run    # simula sem gravar no PostgreSQL
    python migrate_to_postgres.py --truncate   # limpa tabelas e re-migra

CONFIGURACAO (.env ou variaveis de ambiente):
    SQLITE_PATH        caminho do hospital.db   (padrao: ../legado/hospital.db)
    POSTGRES_HOST      host do PostgreSQL        (padrao: localhost)
    POSTGRES_PORT      porta                     (padrao: 5432)
    POSTGRES_DB        nome do banco             (padrao: hmpcf)
    POSTGRES_USER      usuario                   (padrao: postgres)
    POSTGRES_PASSWORD  senha                     (obrigatorio — sem valor padrao)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

# ── Dependencias externas ─────────────────────────────────────────────────────

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 nao instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    _BASE_DIR_ENV = os.path.dirname(os.path.abspath(__file__))
    for _env_path in [
        os.path.join(_BASE_DIR_ENV, ".env"),
        os.path.join(_BASE_DIR_ENV, "..", "backend", ".env"),
    ]:
        if os.path.exists(_env_path):
            load_dotenv(_env_path)
            break
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACAO
# ══════════════════════════════════════════════════════════════════════════════

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SQLITE_PATH       = os.getenv("SQLITE_PATH",       os.path.normpath(os.path.join(_BASE_DIR, "..", "legado", "hospital.db")))
POSTGRES_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB",       "hmpcf")
POSTGRES_USER     = os.getenv("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
LOG_FILE          = os.getenv("LOG_FILE",           os.path.join(_BASE_DIR, "migration.log"))
BATCH_SIZE        = int(os.getenv("BATCH_SIZE",    "500"))

# Valores fixos de faturamento BPA (injetados em todos os registros)
IBGE_PADRAO      = "240360"
CEPPCN_PADRAO    = "59575000"
CO_LOGRAD_PADRAO = "081"


# ══════════════════════════════════════════════════════════════════════════════
#  DDL — estrutura das tabelas
# ══════════════════════════════════════════════════════════════════════════════

DDL_ENUMS = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'classificacao_risco_enum') THEN
        CREATE TYPE classificacao_risco_enum AS ENUM
            ('VERMELHO','LARANJA','AMARELO','VERDE','AZUL');
    END IF;
END $$;
"""

DDL_PACIENTES = """
CREATE TABLE IF NOT EXISTS pacientes (
    id            SERIAL        PRIMARY KEY,
    cns           VARCHAR(15)   UNIQUE,
    num_cpf       VARCHAR(11)   UNIQUE,
    nome          VARCHAR(100),
    dtnasc        VARCHAR(8),
    sexo          CHAR(1)       CHECK (sexo IN ('M','F','I')),
    raca          VARCHAR(2),
    maepcn        VARCHAR(100),
    logpcn        VARCHAR(100),
    numpcn        VARCHAR(100),
    bairro_pcnte  VARCHAR(100),
    ddtel_pcnte   VARCHAR(2),
    tel_pcnte     VARCHAR(9),
    ibge          VARCHAR(6)    NOT NULL DEFAULT '240360',
    ceppcn        VARCHAR(8)    NOT NULL DEFAULT '59575000',
    co_lograd     VARCHAR(3)    NOT NULL DEFAULT '081',
    nome_social   VARCHAR(100),
    idade         VARCHAR(50),
    civil         VARCHAR(50),
    ocupacao      VARCHAR(100),
    responsavel   VARCHAR(100),
    cidade        VARCHAR(100),
    estado        VARCHAR(2),
    nacionalidade VARCHAR(50)   NOT NULL DEFAULT '010',
    naturalidade  VARCHAR(100),
    migrated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

DDL_PACIENTES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_pac_cpf  ON pacientes (num_cpf);",
    "CREATE INDEX IF NOT EXISTS idx_pac_nome ON pacientes (nome);",
    "CREATE INDEX IF NOT EXISTS idx_pac_cns  ON pacientes (cns);",
]

DDL_ATENDIMENTOS = """
CREATE TABLE IF NOT EXISTS recepcao_atendimentos (
    id                    SERIAL                    PRIMARY KEY,
    paciente_id           INTEGER                   NOT NULL
                                                    REFERENCES pacientes(id)
                                                    ON DELETE RESTRICT ON UPDATE CASCADE,
    data_atendimento      TIMESTAMPTZ               NOT NULL DEFAULT NOW(),
    classificacao_risco   classificacao_risco_enum,
    registro              SMALLINT,
    procedencia           TEXT,
    observacoes           TEXT,
    historia_clinica      TEXT,
    hipotese_diagnostica  TEXT,
    created_at            TIMESTAMPTZ               NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ               NOT NULL DEFAULT NOW()
);
"""

DDL_ATD_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_atd_pac  ON recepcao_atendimentos (paciente_id);",
    "CREATE INDEX IF NOT EXISTS idx_atd_data ON recepcao_atendimentos (data_atendimento);",
]


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("hmpcf.migration")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    try:
        out = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", closefd=False)
    except Exception:
        out = sys.stdout
    ch = logging.StreamHandler(out)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = _setup_logging()


# ══════════════════════════════════════════════════════════════════════════════
#  CONEXOES
# ══════════════════════════════════════════════════════════════════════════════

def conectar_sqlite() -> sqlite3.Connection:
    path = os.path.abspath(SQLITE_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Banco SQLite nao encontrado: {path}")
    uri = "file:///{}?mode=ro".format(path.replace("\\", "/").lstrip("/"))
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    log.info(f"SQLite (read-only): {path}")
    return conn


def conectar_postgres() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=10,
    )
    conn.autocommit = False
    log.info(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    return conn


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDACAO MATEMATICA — CPF e CNS
# ══════════════════════════════════════════════════════════════════════════════

def _cpf_valido(cpf: str) -> bool:
    """Valida CPF pelo algoritmo de digito verificador (modulo 11)."""
    d = re.sub(r"\D", "", str(cpf or ""))
    if len(d) != 11 or re.match(r"^(\d)\1{10}$", d):
        return False
    soma = sum(int(d[i]) * (10 - i) for i in range(9))
    dig1 = 0 if soma % 11 < 2 else 11 - soma % 11
    if dig1 != int(d[9]):
        return False
    soma = sum(int(d[i]) * (11 - i) for i in range(10))
    dig2 = 0 if soma % 11 < 2 else 11 - soma % 11
    return dig2 == int(d[10])


def _cns_valido(cns: str) -> bool:
    """Valida CNS/SUS pelo algoritmo DATASUS (soma ponderada divisivel por 11)."""
    d = re.sub(r"\D", "", str(cns or ""))
    if len(d) != 15 or d[0] not in "12789":
        return False
    return sum(int(d[i]) * (15 - i) for i in range(15)) % 11 == 0


# ══════════════════════════════════════════════════════════════════════════════
#  NORMALIZACAO DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

def _s(v) -> str:
    return str(v).strip() if v is not None else ""


def _get(row: sqlite3.Row, key: str) -> str:
    """Acesso seguro a sqlite3.Row — retorna '' para colunas inexistentes."""
    try:
        v = row[key]
        return _s(v)
    except (IndexError, KeyError):
        return ""


def _trunc(v, maxlen: int, default: str = "") -> str:
    s = _s(v) or default
    return s[:maxlen]


def _apenas_num(v) -> str:
    return re.sub(r"\D", "", _s(v))


def norm_cpf(v) -> Optional[str]:
    d = _apenas_num(v)
    if not d or len(d) != 11:
        return None
    return d if _cpf_valido(d) else None


def norm_cns(v) -> Optional[str]:
    d = _apenas_num(v)
    if not d or len(d) != 15:
        return None
    return d if _cns_valido(d) else None


def norm_dtnasc(v) -> Optional[str]:
    """Converte data de nascimento para YYYYMMDD. Aceita DD/MM/YYYY, YYYY-MM-DD, YYYYMMDD."""
    raw = _s(v)
    if not raw:
        return None
    num = _apenas_num(raw)
    ano_max = datetime.now().year
    for fmt, alvo in [
        ("%Y-%m-%d", raw),
        ("%d/%m/%Y", raw),
        ("%Y%m%d",   num),
        ("%d%m%Y",   num),
    ]:
        if len(alvo) not in (8, 10):
            continue
        try:
            dt = datetime.strptime(alvo, fmt)
            if 1900 <= dt.year <= ano_max:
                return dt.strftime("%Y%m%d")
        except ValueError:
            continue
    return None


def norm_sexo(v) -> str:
    s = _s(v).upper()[:1]
    return s if s in ("M", "F") else "I"


_RACA_MAP: dict[str, str] = {
    "1": "01", "01": "01", "BRANCA":   "01",
    "2": "02", "02": "02", "PRETA":    "02",
    "3": "03", "03": "03", "PARDA":    "03",
    "4": "04", "04": "04", "AMARELA":  "04",
    "5": "05", "05": "05", "INDIGENA": "05",
}


def norm_raca(v) -> Optional[str]:
    raw = _s(v).upper()
    raw = unicodedata.normalize("NFD", raw)
    raw = "".join(c for c in raw if unicodedata.category(c) != "Mn")
    return _RACA_MAP.get(raw)


def norm_tel(v) -> Tuple[Optional[str], Optional[str]]:
    """Separa DDD (2 digitos) do numero de telefone."""
    d = _apenas_num(v)
    if not d:
        return None, None
    if d.startswith("0") and len(d) >= 11:
        d = d[1:]
    if len(d) >= 10:
        return d[:2], d[2:11]
    return None, d[:9] or None


# ══════════════════════════════════════════════════════════════════════════════
#  CONTADORES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContPac:
    total:        int  = 0
    migrados:     int  = 0
    duplicatas:   int  = 0
    sem_doc:      int  = 0
    cpf_invalido: int  = 0
    cns_invalido: int  = 0
    erros:        int  = 0
    avisos:       list = field(default_factory=list)

    def avisar(self, ref: str, msg: str) -> None:
        self.avisos.append(f"{ref or '?'} | {msg}")
        log.debug(f"AVISO {ref or '?'} | {msg}")

    @property
    def ok(self) -> bool:
        return self.erros == 0


@dataclass
class ContAtd:
    total:      int = 0
    migrados:   int = 0
    duplicatas: int = 0
    sem_pac:    int = 0
    erros:      int = 0

    @property
    def ok(self) -> bool:
        return self.erros == 0


# ══════════════════════════════════════════════════════════════════════════════
#  DDL — criar tabelas
# ══════════════════════════════════════════════════════════════════════════════

def criar_tabelas(pg: psycopg2.extensions.connection, dry_run: bool) -> None:
    log.info("Criando tabelas (se nao existirem)...")
    if dry_run:
        log.info("  [dry-run] DDL ignorado.")
        return
    with pg.cursor() as cur:
        cur.execute(DDL_ENUMS)
        cur.execute(DDL_PACIENTES)
        for idx in DDL_PACIENTES_IDX:
            cur.execute(idx)
        cur.execute(DDL_ATENDIMENTOS)
        for idx in DDL_ATD_IDX:
            cur.execute(idx)
    pg.commit()
    log.info("  Tabelas pacientes e recepcao_atendimentos prontas.")


def truncar_tabelas(pg: psycopg2.extensions.connection) -> None:
    log.warning("TRUNCANDO recepcao_atendimentos e pacientes (RESTART IDENTITY)...")
    with pg.cursor() as cur:
        cur.execute("TRUNCATE TABLE recepcao_atendimentos, pacientes RESTART IDENTITY;")
    pg.commit()
    log.warning("Tabelas truncadas.")


# ══════════════════════════════════════════════════════════════════════════════
#  ETAPA 1 — PACIENTES
# ══════════════════════════════════════════════════════════════════════════════

_COLS_PAC: tuple[str, ...] = (
    "cns", "num_cpf", "nome", "dtnasc", "sexo", "raca",
    "maepcn", "logpcn", "numpcn", "bairro_pcnte",
    "ddtel_pcnte", "tel_pcnte",
    "ibge", "ceppcn", "co_lograd",
    "nome_social", "idade", "civil", "ocupacao",
    "responsavel", "cidade", "estado", "nacionalidade",
    "naturalidade",
)

_INSERT_PAC = f"INSERT INTO pacientes ({', '.join(_COLS_PAC)}) VALUES %s"


def transformar_pac(row: sqlite3.Row, c: ContPac) -> Optional[tuple]:
    cpf_raw = _get(row, "cpf")
    sus_raw = _get(row, "sus")
    try:
        cns     = norm_cns(sus_raw)
        num_cpf = norm_cpf(cpf_raw)
        nome    = _trunc(_get(row, "nome").upper(),      100)
        dtnasc  = norm_dtnasc(_get(row, "dn"))
        sexo    = norm_sexo(_get(row, "sexo"))
        raca    = norm_raca(_get(row, "raca"))
        maepcn  = _trunc(_get(row, "mae"),               100) or None
        logpcn  = _trunc(_get(row, "endereco"),          100) or None
        numpcn  = _trunc(_get(row, "numero"),            100) or None
        bairro  = _trunc(_get(row, "bairro"),            100) or None
        ddd, tel = norm_tel(_get(row, "tel"))

        nome_social  = _trunc(_get(row, "nomeSocial"),  100) or None
        idade        = _trunc(_get(row, "idade"),         50) or None
        civil        = _trunc(_get(row, "civil"),         50) or None
        ocupacao     = _trunc(_get(row, "ocupacao"),     100) or None
        responsavel  = _trunc(_get(row, "responsavel"),  100) or None
        cidade       = _trunc(_get(row, "cidade"),       100) or None
        estado       = _get(row, "estado").upper()[:2] or None
        nacionalidade = _trunc(_get(row, "naturalidade"), 50) or None

        # Alertas de qualidade (nao descartam o registro)
        if not nome:
            c.avisar(cpf_raw or sus_raw, "NOME vazio")
        if _get(row, "dn") and dtnasc is None:
            c.avisar(cpf_raw or sus_raw, f"data invalida ignorada: '{_get(row, 'dn')}'")
        if sexo == "I" and _get(row, "sexo"):
            c.avisar(cpf_raw or sus_raw, f"sexo nao reconhecido: '{_get(row, 'sexo')}'")

        return (
            cns, num_cpf, nome, dtnasc, sexo, raca,
            maepcn, logpcn, numpcn, bairro,
            ddd, tel,
            IBGE_PADRAO, CEPPCN_PADRAO, CO_LOGRAD_PADRAO,
            nome_social, idade, civil, ocupacao,
            responsavel, cidade, estado, nacionalidade,
            None,   # naturalidade — nao mapeada nesta migracao
        )

    except Exception as exc:
        c.erros += 1
        log.error(f"ERRO transformar paciente CPF={cpf_raw!r}: {exc}", exc_info=True)
        return None


def _carregar_chaves_pg(pg) -> tuple[set, set]:
    with pg.cursor() as cur:
        cur.execute("SELECT num_cpf FROM pacientes WHERE num_cpf IS NOT NULL")
        cpfs = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT cns FROM pacientes WHERE cns IS NOT NULL")
        cnss = {r[0] for r in cur.fetchall()}
    log.info(f"  PG existente: {len(cpfs):,} CPFs | {len(cnss):,} CNSs")
    return cpfs, cnss


def migrar_pacientes(sq: sqlite3.Connection, pg, dry_run: bool) -> ContPac:
    c = ContPac()
    cpfs_pg, cnss_pg = _carregar_chaves_pg(pg)

    rows = sq.execute("SELECT * FROM pacientes ORDER BY ROWID").fetchall()
    c.total = len(rows)
    log.info(f"  SQLite pacientes: {c.total:,}")
    if not c.total:
        log.warning("  Nenhum registro na tabela pacientes do SQLite.")
        return c

    batch: list = []
    inicio = datetime.now()

    for row in rows:
        cpf_raw = _get(row, "cpf")
        sus_raw = _get(row, "sus")
        cpf = norm_cpf(cpf_raw)
        cns = norm_cns(sus_raw)

        # Conta documentos matematicamente invalidos (mas continua processando)
        cpf_digits = _apenas_num(cpf_raw)
        if cpf_digits and len(cpf_digits) == 11 and cpf is None:
            c.cpf_invalido += 1

        cns_digits = _apenas_num(sus_raw)
        if cns_digits and len(cns_digits) == 15 and cns is None:
            c.cns_invalido += 1

        # Deduplicacao por CPF ou CNS exato
        if (cpf and cpf in cpfs_pg) or (cns and cns in cnss_pg):
            c.duplicatas += 1
            continue

        # Sem CPF valido nem CNS valido -> descarta
        if not cpf and not cns:
            c.sem_doc += 1
            log.debug(f"Sem doc valido: nome={_get(row, 'nome')!r}")
            continue

        rec = transformar_pac(row, c)
        if rec is None:
            continue

        batch.append(rec)

        # Atualiza chaves locais para dedup dentro da propria fonte
        if cpf:
            cpfs_pg.add(cpf)
        if cns:
            cnss_pg.add(cns)

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _inserir_batch_pac(pg, batch, c)
            else:
                c.migrados += len(batch)
            _log_prog_pac(c, inicio)
            batch.clear()

    if batch:
        if not dry_run:
            _inserir_batch_pac(pg, batch, c)
        else:
            c.migrados += len(batch)

    return c


def _inserir_batch_pac(pg, batch: list, c: ContPac) -> None:
    try:
        with pg.cursor() as cur:
            execute_values(cur, _INSERT_PAC, batch, page_size=BATCH_SIZE)
        pg.commit()
        c.migrados += len(batch)
    except Exception as exc:
        pg.rollback()
        log.warning(f"Falha no lote de pacientes ({exc}). Tentando individual...")
        _inserir_pac_individual(pg, batch, c)


def _inserir_pac_individual(pg, batch: list, c: ContPac) -> None:
    sql = (
        f"INSERT INTO pacientes ({', '.join(_COLS_PAC)}) "
        f"VALUES ({', '.join(['%s'] * len(_COLS_PAC))})"
    )
    for rec in batch:
        try:
            with pg.cursor() as cur:
                cur.execute(sql, rec)
            pg.commit()
            c.migrados += 1
        except Exception as exc:
            pg.rollback()
            c.erros += 1
            log.error(f"ERRO SQL paciente | num_cpf={rec[1]!r} | {exc}")


def _log_prog_pac(c: ContPac, inicio: datetime) -> None:
    feitos = c.migrados + c.duplicatas + c.sem_doc + c.erros
    pct    = feitos / c.total * 100 if c.total else 0
    seg    = max((datetime.now() - inicio).seconds, 1)
    log.info(
        f"  {feitos:>6,}/{c.total:,} ({pct:5.1f}%)  "
        f"migrados={c.migrados:,}  dup={c.duplicatas:,}  "
        f"sem_doc={c.sem_doc:,}  erros={c.erros:,}  [{seg}s]"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ETAPA 2 — ATENDIMENTOS
# ══════════════════════════════════════════════════════════════════════════════

_COLS_ATD: tuple[str, ...] = (
    "paciente_id", "data_atendimento", "registro", "procedencia",
)

_INSERT_ATD = f"INSERT INTO recepcao_atendimentos ({', '.join(_COLS_ATD)}) VALUES %s"


def _construir_mapa_pacs(pg) -> dict[str, int]:
    mapa: dict[str, int] = {}
    with pg.cursor() as cur:
        cur.execute("SELECT id, num_cpf FROM pacientes WHERE num_cpf IS NOT NULL")
        for pid, cpf in cur.fetchall():
            mapa[cpf] = pid
        cur.execute("SELECT id, cns FROM pacientes WHERE cns IS NOT NULL")
        for pid, cns in cur.fetchall():
            mapa[cns] = pid
    log.info(f"  Mapa de pacientes: {len(mapa):,} identificadores (CPF + CNS)")
    return mapa


def _carregar_chaves_atd(pg) -> set[tuple]:
    try:
        with pg.cursor() as cur:
            cur.execute("SELECT paciente_id, data_atendimento FROM recepcao_atendimentos")
            return {(r[0], r[1]) for r in cur.fetchall()}
    except psycopg2.errors.UndefinedTable:
        pg.rollback()
        return set()


def _norm_dt_atd(data_str: str, hora_str: str) -> Optional[datetime]:
    d = _s(data_str)
    h = _s(hora_str) or "00:00"
    if not d:
        return None
    try:
        return datetime.strptime(f"{d} {h}", "%Y-%m-%d %H:%M")
    except ValueError:
        pass
    try:
        return datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return None


def migrar_atendimentos(sq: sqlite3.Connection, pg, dry_run: bool) -> ContAtd:
    c = ContAtd()
    mapa      = _construir_mapa_pacs(pg)
    chaves_pg = _carregar_chaves_atd(pg)

    rows = sq.execute("SELECT * FROM atendimentos ORDER BY id").fetchall()
    c.total = len(rows)
    log.info(f"  SQLite atendimentos: {c.total:,}")
    if not c.total:
        log.warning("  Nenhum registro na tabela atendimentos do SQLite.")
        return c

    batch: list = []
    inicio = datetime.now()

    for row in rows:
        # A tabela atendimentos usa os nomes antigos: cpf e sus
        cpf_raw = _get(row, "cpf")
        sus_raw = _get(row, "sus")
        cpf = norm_cpf(cpf_raw)
        cns = norm_cns(sus_raw)

        # Resolve paciente_id via CPF ou CNS
        pac_id = None
        if cpf:
            pac_id = mapa.get(cpf)
        if pac_id is None and cns:
            pac_id = mapa.get(cns)

        if pac_id is None:
            c.sem_pac += 1
            log.debug(f"Paciente nao encontrado: CPF={cpf_raw!r} SUS={sus_raw!r}")
            continue

        dt = _norm_dt_atd(_get(row, "data_atendimento"), _get(row, "hora_atendimento"))
        if dt is None:
            c.erros += 1
            log.error(f"Data invalida no atendimento: paciente_id={pac_id}")
            continue

        chave = (pac_id, dt)
        if chave in chaves_pg:
            c.duplicatas += 1
            continue

        reg_raw = _get(row, "registro")
        try:
            registro = int(reg_raw) if reg_raw else None
            if registro is not None and not (-32768 <= registro <= 32767):
                registro = None
        except ValueError:
            registro = None

        proc = _get(row, "procedencia") or None
        batch.append((pac_id, dt, registro, proc))
        chaves_pg.add(chave)

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _inserir_batch_atd(pg, batch, c)
            else:
                c.migrados += len(batch)
            feitos = c.migrados + c.duplicatas + c.sem_pac + c.erros
            pct = feitos / c.total * 100 if c.total else 0
            log.info(
                f"  ATD {feitos:>6,}/{c.total:,} ({pct:5.1f}%)  "
                f"migrados={c.migrados:,}  dup={c.duplicatas:,}  sem_pac={c.sem_pac:,}"
            )
            batch.clear()

    if batch:
        if not dry_run:
            _inserir_batch_atd(pg, batch, c)
        else:
            c.migrados += len(batch)

    return c


def _inserir_batch_atd(pg, batch: list, c: ContAtd) -> None:
    try:
        with pg.cursor() as cur:
            execute_values(cur, _INSERT_ATD, batch, page_size=BATCH_SIZE)
        pg.commit()
        c.migrados += len(batch)
    except Exception as exc:
        pg.rollback()
        log.warning(f"Falha no lote de atendimentos ({exc}). Tentando individual...")
        _inserir_atd_individual(pg, batch, c)


def _inserir_atd_individual(pg, batch: list, c: ContAtd) -> None:
    sql = (
        f"INSERT INTO recepcao_atendimentos ({', '.join(_COLS_ATD)}) "
        f"VALUES ({', '.join(['%s'] * len(_COLS_ATD))})"
    )
    for rec in batch:
        try:
            with pg.cursor() as cur:
                cur.execute(sql, rec)
            pg.commit()
            c.migrados += 1
        except Exception as exc:
            pg.rollback()
            c.erros += 1
            log.error(f"ERRO SQL atendimento paciente_id={rec[0]}: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  RELATORIO FINAL
# ══════════════════════════════════════════════════════════════════════════════

def exibir_relatorio(c: ContPac, c_atd: ContAtd, dry_run: bool, duracao) -> None:
    SEP  = "=" * 62
    SEP2 = "-" * 62
    log.info("")
    log.info(SEP)
    log.info("  RELATORIO FINAL DE MIGRACAO")
    log.info("  HMPCF - Hospital Municipal Pedro Coutinho Filho")
    if dry_run:
        log.info("  [DRY-RUN] Nenhum dado foi gravado no PostgreSQL")
    log.info(SEP)
    log.info(f"  Origem  : {os.path.abspath(SQLITE_PATH)}")
    log.info(f"  Destino : {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

    log.info(SEP2)
    log.info("  PACIENTES")
    log.info(SEP2)
    log.info(f"  Total SQLite            : {c.total:>8,}")
    log.info(f"  Migrados                : {c.migrados:>8,}")
    log.info(f"  Duplicatas (pulados)    : {c.duplicatas:>8,}  (CPF ou CNS ja existia)")
    log.info(f"  Sem CPF nem CNS valido  : {c.sem_doc:>8,}  (descartados)")
    log.info(f"  CPF invalido (mod 11)   : {c.cpf_invalido:>8,}  (num_cpf = NULL)")
    log.info(f"  CNS invalido (DATASUS)  : {c.cns_invalido:>8,}  (cns = NULL)")
    log.info(f"  Erros                   : {c.erros:>8,}")
    log.info(f"  Avisos de qualidade     : {len(c.avisos):>8,}")

    if c.total:
        processados = c.migrados + c.duplicatas + c.sem_doc + c.erros
        log.info(f"  Processados             : {processados / c.total * 100:>7.1f}%")

    if c.avisos:
        log.info(SEP2)
        log.info(f"  AVISOS (primeiros 20 de {len(c.avisos):,}):")
        for aviso in c.avisos[:20]:
            log.warning(f"    [!] {aviso}")
        if len(c.avisos) > 20:
            log.info(f"    ... +{len(c.avisos) - 20} avisos — veja: {LOG_FILE}")

    log.info(SEP2)
    log.info("  ATENDIMENTOS")
    log.info(SEP2)
    log.info(f"  Total SQLite            : {c_atd.total:>8,}")
    log.info(f"  Migrados                : {c_atd.migrados:>8,}")
    log.info(f"  Duplicatas (pulados)    : {c_atd.duplicatas:>8,}  (paciente_id + datetime)")
    log.info(f"  Sem paciente encontrado : {c_atd.sem_pac:>8,}  (CPF/CNS nao no PG)")
    log.info(f"  Erros                   : {c_atd.erros:>8,}")

    if c_atd.total:
        processados_atd = c_atd.migrados + c_atd.duplicatas + c_atd.sem_pac + c_atd.erros
        log.info(f"  Processados             : {processados_atd / c_atd.total * 100:>7.1f}%")

    log.info(SEP2)
    ok_geral = c.ok and c_atd.ok
    log.info(f"  STATUS   : {'CONCLUIDA COM SUCESSO' if ok_geral else 'CONCLUIDA COM ERROS'}")
    log.info(f"  Duracao  : {duracao}")
    log.info(f"  Log      : {os.path.abspath(LOG_FILE)}")
    log.info(SEP)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI / MAIN
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Migracao completa: hospital.db (SQLite) -> PostgreSQL (HMPCF)\n"
            "  Cria as tabelas, migra pacientes e atendimentos.\n"
            "  SQLite aberto em SOMENTE LEITURA — nenhuma escrita no legado.\n"
            "  Seguro para rodar mais de uma vez (deduplicacao automatica)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dry-run",  action="store_true",
                   help="Processa tudo sem gravar no PostgreSQL.")
    p.add_argument("--truncate", action="store_true",
                   help="Limpa as tabelas antes de inserir. IRREVERSIVEL.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    SEP = "=" * 62
    log.info(SEP)
    log.info("  MIGRACAO SQLite => PostgreSQL")
    log.info("  HMPCF - Hospital Municipal Pedro Coutinho Filho")
    log.info(SEP)
    log.info(f"  Origem  : {os.path.abspath(SQLITE_PATH)}")
    log.info(f"  Destino : {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    log.info(f"  Lote    : {BATCH_SIZE} registros por INSERT")
    if args.dry_run:
        log.info("  Modo    : DRY-RUN (nenhum dado sera gravado)")
    if args.truncate:
        log.info("  Atencao : --truncate ativo - tabelas serao limpas antes")
    log.info("")

    sq = pg = None
    inicio = datetime.now()
    c = ContPac()
    c_atd = ContAtd()

    try:
        sq = conectar_sqlite()
        pg = conectar_postgres()

        # Etapa 0: criar tabelas
        log.info("-- Etapa 0: Estrutura das tabelas --")
        criar_tabelas(pg, dry_run=args.dry_run)

        if not args.dry_run and args.truncate:
            truncar_tabelas(pg)

        # Etapa 1: pacientes
        log.info("")
        log.info("-- Etapa 1: Migracao de pacientes --")
        c = migrar_pacientes(sq, pg, dry_run=args.dry_run)

        # Etapa 2: atendimentos
        log.info("")
        log.info("-- Etapa 2: Migracao de atendimentos --")
        c_atd = migrar_atendimentos(sq, pg, dry_run=args.dry_run)

    except FileNotFoundError as exc:
        log.critical(str(exc))
        sys.exit(1)
    except psycopg2.OperationalError as exc:
        log.critical(f"Falha de conexao com o PostgreSQL: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        log.warning("Migracao interrompida pelo usuario.")
        sys.exit(1)
    except Exception as exc:
        log.critical(f"Erro inesperado: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        if sq:
            sq.close()
        if pg and not pg.closed:
            pg.close()

    duracao = datetime.now() - inicio
    exibir_relatorio(c, c_atd, dry_run=args.dry_run, duracao=duracao)
    sys.exit(0 if (c.ok and c_atd.ok) else 1)
