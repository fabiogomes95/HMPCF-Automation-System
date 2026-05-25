#!/usr/bin/env python3
"""
recreate_pacientes.py
=====================
Recria a tabela `pacientes` no PostgreSQL com a estrutura exata do
padrao Firebird/CADCNS (BPA-SUS) e migra os dados do hospital.db (SQLite).

Uso:
    python recreate_pacientes.py              # executa tudo
    python recreate_pacientes.py --dry-run    # simula sem gravar
    python recreate_pacientes.py --skip-drop  # nao dropa; falha se tabela existe
"""

import argparse
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime
from typing import Optional

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 nao instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

# ── Configuracao ──────────────────────────────────────────────────────────────

_BASE       = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(_BASE, "hospital.db")
LOG_FILE    = os.path.join(_BASE, "recreate_pacientes.log")
BATCH_SIZE  = 500

PG_DSN = dict(
    host="localhost",
    port=5432,
    dbname="hmpcf",
    user="postgres",
    password="hmpcf2024",
    connect_timeout=10,
)

# ── Logging ───────────────────────────────────────────────────────────────────

def _setup_log() -> logging.Logger:
    log = logging.getLogger("recreate_pacientes")
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(ch)
    return log

log = _setup_log()

# ── DDL ───────────────────────────────────────────────────────────────────────

DDL_PACIENTES = """
CREATE TABLE pacientes (
    id            SERIAL          PRIMARY KEY,
    cns           VARCHAR(15)     UNIQUE,
    num_cpf       VARCHAR(11),
    nome          VARCHAR(50),
    dtnasc        VARCHAR(8),
    sexo          CHAR(1)         CHECK (sexo IN ('M','F','I')),
    raca          VARCHAR(2),
    maepcn        VARCHAR(50),
    logpcn        VARCHAR(50)     NOT NULL DEFAULT 'PRINCIPAL',
    numpcn        VARCHAR(5)      NOT NULL DEFAULT 'S/N',
    bairro_pcnte  VARCHAR(50)     NOT NULL DEFAULT 'CENTRO',
    nmres         VARCHAR(50),
    ddtel_pcnte   VARCHAR(2),
    tel_pcnte     VARCHAR(9),
    ibge          VARCHAR(6),
    ceppcn        VARCHAR(8),
    co_lograd     VARCHAR(3),
    nome_social   VARCHAR(50),
    idade         VARCHAR(50),
    civil         VARCHAR(50),
    ocupacao      VARCHAR(50),
    responsavel   VARCHAR(50),
    cidade        VARCHAR(50),
    estado        VARCHAR(2),
    nacionalidade VARCHAR(50),
    migrated_at   TIMESTAMPTZ     DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_INDICES = [
    'CREATE INDEX idx_pac_cpf  ON pacientes (num_cpf);',
    'CREATE INDEX idx_pac_nome ON pacientes (nome);',
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _s(v) -> str:
    """None/qualquer coisa -> string limpa."""
    return str(v).strip() if v is not None else ""


def _trunc(v, maxlen: int, default: str = "") -> str:
    """String -> truncada em maxlen; None vira default."""
    s = _s(v) or default
    return s[:maxlen]


def apenas_num(v) -> str:
    return re.sub(r"\D", "", _s(v))


def norm_cpf(v) -> Optional[str]:
    d = apenas_num(v)
    if not d or len(d) > 11:
        return None
    return d if len(d) >= 8 else None


def norm_cns(v) -> Optional[str]:
    d = apenas_num(v)
    return d[:15] if d else None


def norm_dtnasc(v) -> str:
    """YYYY-MM-DD | DD/MM/YYYY | YYYYMMDD -> YYYYMMDD; falha -> ''"""
    raw = _s(v)
    if not raw:
        return ""
    for fmt, alvo in [
        ("%Y-%m-%d",  raw),
        ("%d/%m/%Y",  raw),
        ("%Y%m%d",    apenas_num(raw)),
        ("%d%m%Y",    apenas_num(raw)),
    ]:
        candidate = alvo if len(alvo) in (8, 10) else ""
        if not candidate:
            continue
        try:
            dt = datetime.strptime(candidate, fmt)
            if 1900 <= dt.year <= datetime.now().year:
                return dt.strftime("%Y%m%d")
        except ValueError:
            pass
    return ""


def norm_sexo(v) -> str:
    s = _s(v).upper()
    return s if s in ("M", "F") else "I"


_RACA_MAP = {
    "BRANCA": "01", "PRETA": "02", "PARDA": "03",
    "AMARELA": "04", "INDIGENA": "05", "INDIGENA": "05",
    "01": "01", "02": "02", "03": "03", "04": "04", "05": "05",
}

def norm_raca(v) -> str:
    return _RACA_MAP.get(_s(v).upper(), "")


def norm_tel(v):
    """
    '(84) 99166-8229' -> ('84', '991668229')
    Retorna (ddd: str, tel: str) — nunca None, sempre string (pode ser '').
    """
    d = apenas_num(v)
    if not d:
        return "", ""
    if d.startswith("0") and len(d) >= 11:
        d = d[1:]
    if len(d) >= 10:
        return d[:2], d[2:11]        # ddd 2 digitos, tel ate 9 digitos
    return "", d[:9]


# ── Transformar linha do SQLite ───────────────────────────────────────────────

# Ordem exata das colunas no INSERT
_COLS = (
    "cns", "num_cpf", "nome", "dtnasc", "sexo", "raca",
    "maepcn", "logpcn", "numpcn", "bairro_pcnte", "nmres",
    "ddtel_pcnte", "tel_pcnte",
    "ibge", "ceppcn", "co_lograd",
    "nome_social", "idade", "civil", "ocupacao",
    "responsavel", "cidade", "estado", "nacionalidade",
)

_INSERT_SQL = (
    f"INSERT INTO pacientes ({', '.join(_COLS)}) VALUES %s"
)


def transformar(row: sqlite3.Row) -> Optional[tuple]:
    try:
        cns     = norm_cns(row["sus"])
        cpf     = norm_cpf(row["cpf"])
        nome    = _trunc(row["nome"],       50)
        dtnasc  = norm_dtnasc(row["dn"])
        sexo    = norm_sexo(row["sexo"])
        raca    = norm_raca(row["raca"])
        maepcn  = _trunc(row["mae"],        50)
        logpcn  = _trunc(row["endereco"],   50, default="PRINCIPAL")
        numpcn  = _trunc(row["numero"],      5, default="S/N")
        bairro  = _trunc(row["bairro"],     50, default="CENTRO")
        nmres   = _trunc(row["naturalidade"],50)
        ddd, tel = norm_tel(row["tel"])

        # Novos campos BPA — nao existem no SQLite, ficam vazios
        ibge     = ""
        ceppcn   = ""
        co_lograd = ""

        nome_social  = _trunc(row["nomeSocial"],  50)
        idade        = _trunc(row["idade"],        50)
        civil        = _trunc(row["civil"],        50)
        ocupacao     = _trunc(row["ocupacao"],     50)
        responsavel  = _trunc(row["responsavel"],  50)
        cidade       = _trunc(row["cidade"],       50)
        estado       = _trunc(row["estado"],        2)
        nacionalidade = _trunc(row["naturalidade"], 50)

        return (
            cns, cpf, nome, dtnasc, sexo, raca,
            maepcn, logpcn, numpcn, bairro, nmres,
            ddd, tel,
            ibge, ceppcn, co_lograd,
            nome_social, idade, civil, ocupacao,
            responsavel, cidade, estado, nacionalidade,
        )
    except Exception as exc:
        log.error(f"Erro ao transformar cpf={_s(row['cpf'])}: {exc}")
        return None


# ── Banco de dados ────────────────────────────────────────────────────────────

def abrir_sqlite() -> sqlite3.Connection:
    if not os.path.exists(SQLITE_PATH):
        raise FileNotFoundError(f"hospital.db nao encontrado: {SQLITE_PATH}")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    log.info(f"SQLite: {SQLITE_PATH}")
    return conn


def abrir_pg() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(**PG_DSN)
    conn.autocommit = False
    log.info(f"PostgreSQL: {PG_DSN['host']}:{PG_DSN['port']}/{PG_DSN['dbname']}")
    return conn


# ── DDL: recriar tabela ───────────────────────────────────────────────────────

def recriar_tabela(pg: psycopg2.extensions.connection, skip_drop: bool, dry_run: bool):
    with pg.cursor() as cur:
        # Verifica se a tabela ja existe
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'pacientes'
        """)
        existe = cur.fetchone()[0] > 0

        if existe and skip_drop:
            raise RuntimeError(
                "Tabela 'pacientes' ja existe e --skip-drop foi usado. "
                "Remova a flag para recriar."
            )

        if existe:
            log.info("Removendo FK de recepcao_atendimentos (se existir)...")
            # Remove constraint de FK para poder dropar pacientes
            cur.execute("""
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'recepcao_atendimentos'::regclass
                  AND contype = 'f'
                  AND confrelid = 'pacientes'::regclass
            """)
            fks = [r[0] for r in cur.fetchall()]
            for fk in fks:
                if not dry_run:
                    cur.execute(
                        f'ALTER TABLE recepcao_atendimentos DROP CONSTRAINT "{fk}"'
                    )
                log.info(f"  FK removida: {fk}")

            log.info("Dropando tabela pacientes...")
            if not dry_run:
                cur.execute("DROP TABLE pacientes CASCADE")

        log.info("Criando tabela pacientes (estrutura BPA/Firebird)...")
        if not dry_run:
            cur.execute(DDL_PACIENTES)
            for idx_sql in DDL_INDICES:
                cur.execute(idx_sql)
            pg.commit()
            log.info("Tabela criada com indices.")
        else:
            log.info("[dry-run] DDL nao executado.")


# ── Migracao ──────────────────────────────────────────────────────────────────

def migrar(sqlite_conn, pg: psycopg2.extensions.connection, dry_run: bool):
    rows = sqlite_conn.execute("SELECT * FROM pacientes ORDER BY ROWID").fetchall()
    total = len(rows)
    log.info(f"Pacientes no SQLite: {total:,}")

    # Chaves ja inseridas (dedup dentro da propria fonte)
    cpfs_vistos: set[str] = set()
    cnss_vistos: set[str] = set()

    batch        = []
    inseridos    = 0
    pulados_dup  = 0
    erros        = 0

    for row in rows:
        cpf = norm_cpf(row["cpf"])
        cns = norm_cns(row["sus"])

        # Dedup: pula se CPF ou CNS ja apareceu nesta execucao
        if (cpf and cpf in cpfs_vistos) or (cns and cns in cnss_vistos):
            pulados_dup += 1
            continue

        rec = transformar(row)
        if rec is None:
            erros += 1
            continue

        batch.append(rec)
        if cpf: cpfs_vistos.add(cpf)
        if cns: cnss_vistos.add(cns)

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _inserir_batch(pg, batch, inseridos, erros)
            inseridos += len(batch)
            batch.clear()
            log.info(f"  {inseridos:,} inseridos, {pulados_dup:,} duplicatas puladas...")

    if batch:
        if not dry_run:
            _inserir_batch(pg, batch, inseridos, erros)
        inseridos += len(batch)

    log.info(
        f"Migracao: total={total:,} | inseridos={inseridos:,} | "
        f"duplicatas={pulados_dup:,} | erros={erros}"
    )
    return inseridos, pulados_dup, erros


def _inserir_batch(pg, batch: list, inseridos_atual: int, erros_ref: int):
    try:
        with pg.cursor() as cur:
            execute_values(cur, _INSERT_SQL, batch, page_size=BATCH_SIZE)
        pg.commit()
    except Exception as exc:
        pg.rollback()
        log.warning(f"Falha no lote ({exc}). Tentando individual...")
        _inserir_individual(pg, batch, erros_ref)


def _inserir_individual(pg, batch: list, erros_ref: int):
    ncols = len(batch[0])
    sql = _INSERT_SQL.split("VALUES")[0].strip() + f" VALUES ({', '.join(['%s'] * ncols)})"
    for rec in batch:
        try:
            with pg.cursor() as cur:
                cur.execute(sql, rec)
            pg.commit()
        except Exception as exc:
            pg.rollback()
            log.error(f"Erro individual cpf={rec[1]!r}: {exc}")


# ── Restaurar FK ──────────────────────────────────────────────────────────────

def restaurar_fk(pg: psycopg2.extensions.connection, dry_run: bool):
    """Recria a FK de recepcao_atendimentos -> pacientes."""
    sql = """
        ALTER TABLE recepcao_atendimentos
        ADD CONSTRAINT fk_atd_paciente
        FOREIGN KEY (paciente_id) REFERENCES pacientes ("ID")
        ON DELETE RESTRICT ON UPDATE CASCADE
    """
    with pg.cursor() as cur:
        # Checa se a FK ja existe (pode ter sido recriada por outro meio)
        cur.execute("""
            SELECT COUNT(*) FROM pg_constraint
            WHERE conrelid = 'recepcao_atendimentos'::regclass
              AND conname = 'fk_atd_paciente'
        """)
        if cur.fetchone()[0] > 0:
            log.info("FK fk_atd_paciente ja existe — nada a fazer.")
            return

    if not dry_run:
        with pg.cursor() as cur:
            cur.execute(sql)
        pg.commit()
        log.info("FK fk_atd_paciente recriada em recepcao_atendimentos.")
    else:
        log.info("[dry-run] FK nao recriada.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Recria pacientes BPA + migra do SQLite")
    ap.add_argument("--dry-run",   action="store_true", help="Simula sem gravar")
    ap.add_argument("--skip-drop", action="store_true", help="Nao dropa; falha se tabela existe")
    args = ap.parse_args()

    SEP = "=" * 58
    log.info(SEP)
    log.info("  RECREATE PACIENTES — SQLite -> PostgreSQL (BPA/Firebird)")
    log.info(f"  Origem  : {SQLITE_PATH}")
    log.info(f"  Destino : {PG_DSN['host']}:{PG_DSN['port']}/{PG_DSN['dbname']}")
    if args.dry_run:
        log.info("  Modo    : DRY-RUN (nenhum dado sera gravado)")
    log.info(SEP)

    inicio = datetime.now()

    sqlite_conn = abrir_sqlite()
    pg_conn     = abrir_pg()

    try:
        log.info("\n-- PASSO 1: Recriar tabela pacientes --")
        recriar_tabela(pg_conn, skip_drop=args.skip_drop, dry_run=args.dry_run)

        log.info("\n-- PASSO 2: Migrar pacientes do SQLite --")
        inseridos, pulados, erros = migrar(sqlite_conn, pg_conn, dry_run=args.dry_run)

        log.info("\n-- PASSO 3: Restaurar FK --")
        restaurar_fk(pg_conn, dry_run=args.dry_run)

    except Exception as exc:
        log.critical(f"Erro fatal: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        sqlite_conn.close()
        if not pg_conn.closed:
            pg_conn.close()

    duracao = datetime.now() - inicio
    log.info(f"\n{SEP}")
    log.info("  RESULTADO")
    log.info(SEP)
    if not args.dry_run:
        log.info(f"  Inseridos   : {inseridos:>7,}")
        log.info(f"  Duplicatas  : {pulados:>7,}")
        log.info(f"  Erros       : {erros:>7,}")
    log.info(f"  Duracao     : {duracao}")
    log.info(f"  Log         : {LOG_FILE}")
    log.info(SEP)

    sys.exit(0 if erros == 0 else 1)


if __name__ == "__main__":
    main()
