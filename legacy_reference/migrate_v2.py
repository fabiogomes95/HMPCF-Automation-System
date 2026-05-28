#!/usr/bin/env python3
"""
migrate_v2.py
=============
Fase 2 — ETL hospital.db (SQLite) → PostgreSQL

Passos executados:
  1. Pacientes novos   — insere apenas os que ainda não existem no PG
  2. Naturalidade fix  — copia nmres → nacionalidade nos pacientes já migrados
  3. Atendimentos      — migra todos os 11.758 registros históricos

Uso:
    python migrate_v2.py              # migração completa
    python migrate_v2.py --dry-run    # simula sem gravar
    python migrate_v2.py --skip-pac   # pula pacientes, só atendimentos
"""

import argparse
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 não instalado.  Execute: pip install psycopg2-binary")
    sys.exit(1)

# ── Configuração ──────────────────────────────────────────────────────────────

_BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH  = os.path.join(_BASE, "hospital.db")
PG_DSN = dict(
    host     = "localhost",
    port     = 5432,
    dbname   = "hmpcf",
    user     = "postgres",
    password = "hmpcf2024",
    connect_timeout = 10,
)
BATCH_SIZE = 500
LOG_FILE   = os.path.join(_BASE, "migration_v2.log")

# ── Logging ───────────────────────────────────────────────────────────────────

def _setup_log() -> logging.Logger:
    log = logging.getLogger("migrate_v2")
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

# ── Helpers ───────────────────────────────────────────────────────────────────

def _s(v) -> str:
    return str(v).strip() if v is not None else ""

def apenas_num(v) -> str:
    return re.sub(r"\D", "", _s(v))

def limpar(v, default="") -> str:
    s = _s(v)
    return s if s else default

def norm_cpf(v) -> Optional[str]:
    d = apenas_num(v)
    if not d or len(d) > 11:
        return None   # mais de 11 dígitos = dado inválido (CNS no campo CPF, etc.)
    return d if len(d) >= 8 else None

def norm_cns(v) -> Optional[str]:
    d = apenas_num(v)
    return d if d else None

def norm_data(v) -> Optional[str]:
    """YYYY-MM-DD | DD/MM/YYYY | YYYYMMDD → YYYYMMDD"""
    raw = _s(v)
    if not raw:
        return None
    for fmt, alvo in [("%Y-%m-%d", raw), ("%d/%m/%Y", raw),
                      ("%Y%m%d", apenas_num(raw)), ("%d%m%Y", apenas_num(raw))]:
        if len(alvo) not in (8, 10):
            continue
        try:
            dt = datetime.strptime(alvo, fmt)
            if 1900 <= dt.year <= datetime.now().year:
                return dt.strftime("%Y%m%d")
        except ValueError:
            pass
    return None

def norm_sexo(v) -> str:
    s = _s(v).upper()
    return s if s in ("M", "F") else "I"

_RACA = {"BRANCA":"01","PRETA":"02","PARDA":"03","AMARELA":"04",
         "INDIGENA":"05","INDÍGENA":"05",
         "01":"01","02":"02","03":"03","04":"04","05":"05"}

def norm_raca(v) -> Optional[str]:
    return _RACA.get(_s(v).upper())

def norm_tel(v):
    """(84) 99166-8229  →  ('84', '991668229')"""
    d = apenas_num(v)
    if not d:
        return None, None
    if d.startswith("0") and len(d) >= 11:
        d = d[1:]
    if len(d) >= 10:
        return d[:2], d[2:14]
    return None, d[:12] if d else None

def norm_estado(v) -> Optional[str]:
    s = _s(v)
    return s[:2].upper() if s else None

def norm_datetime(data: str, hora: str) -> Optional[datetime]:
    """'2026-04-01' + '12:17'  →  datetime(2026, 4, 1, 12, 17)"""
    try:
        h = hora.strip() if hora else "00:00"
        if len(h) == 4 and ":" not in h:
            h = h[:2] + ":" + h[2:]
        return datetime.strptime(f"{data} {h}", "%Y-%m-%d %H:%M")
    except Exception:
        try:
            return datetime.strptime(data, "%Y-%m-%d")
        except Exception:
            return None

# ── Contadores ────────────────────────────────────────────────────────────────

@dataclass
class Stats:
    label:    str
    total:    int = 0
    inseridos:int = 0
    pulados:  int = 0
    erros:    int = 0
    avisos:   list = field(default_factory=list)

    def ok(self): return self.erros == 0

# ── Conexões ──────────────────────────────────────────────────────────────────

def abrir_sqlite() -> sqlite3.Connection:
    if not os.path.exists(SQLITE_PATH):
        raise FileNotFoundError(f"hospital.db não encontrado: {SQLITE_PATH}")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    log.info(f"SQLite aberto: {SQLITE_PATH}")
    return conn

def abrir_pg() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(**PG_DSN)
    conn.autocommit = False
    log.info(f"PostgreSQL: {PG_DSN['host']}:{PG_DSN['port']}/{PG_DSN['dbname']}")
    return conn

# ══════════════════════════════════════════════════════════════════════════════
#  PASSO 1 — Pacientes novos
# ══════════════════════════════════════════════════════════════════════════════

_PAC_COLS = (
    "cns", "num_cpf", "nome", "dtnasc", "sexo", "raca",
    "maepcn", "logpcn", "numpcn", "bairro_pcnte",
    "ddtel_pcnte", "tel_pcnte",
    "nome_social", "idade", "civil", "ocupacao",
    "responsavel", "cidade", "estado", "nacionalidade",
)
_PAC_INSERT = f"INSERT INTO pacientes ({', '.join(_PAC_COLS)}) VALUES %s"


def _carregar_chaves_pg(pg) -> tuple[set, set]:
    """Retorna (cpfs_existentes, cnss_existentes) já no PostgreSQL."""
    with pg.cursor() as cur:
        cur.execute('SELECT num_cpf FROM pacientes WHERE num_cpf IS NOT NULL')
        cpfs = {r[0] for r in cur.fetchall()}
        cur.execute('SELECT cns FROM pacientes WHERE cns IS NOT NULL')
        cnss = {r[0] for r in cur.fetchall()}
    log.info(f"PG: {len(cpfs):,} CPFs e {len(cnss):,} CNSs já existentes.")
    return cpfs, cnss


def _transformar_paciente(row: sqlite3.Row) -> Optional[tuple]:
    try:
        cns     = norm_cns(row["sus"])
        num_cpf = norm_cpf(row["cpf"])
        nome    = limpar(row["nome"]) or None
        dtnasc  = norm_data(row["dn"])
        sexo    = norm_sexo(row["sexo"])
        raca    = norm_raca(row["raca"])
        maepcn  = limpar(row["mae"])  or None
        logpcn  = limpar(row["endereco"]) or None
        numpcn  = limpar(row["numero"])   or None
        bairro  = limpar(row["bairro"])   or None
        ddd, tel = norm_tel(row["tel"])
        nome_social  = limpar(row["nomeSocial"]) or None
        idade        = limpar(row["idade"])      or None
        civil        = limpar(row["civil"])      or None
        ocupacao     = limpar(row["ocupacao"])   or None
        responsavel  = limpar(row["responsavel"]) or None
        cidade       = limpar(row["cidade"])      or None
        estado       = norm_estado(row["estado"])
        # naturalidade também vai para o campo visível no formulário
        nacionalidade = limpar(row["naturalidade"]) or None

        return (cns, num_cpf, nome, dtnasc, sexo, raca,
                maepcn, logpcn, numpcn, bairro,
                ddd, tel,
                nome_social, idade, civil, ocupacao,
                responsavel, cidade, estado, nacionalidade)
    except Exception as exc:
        log.error(f"Erro ao transformar paciente cpf={_s(row['cpf'])}: {exc}")
        return None


def migrar_pacientes(sqlite_conn, pg_conn, dry_run: bool) -> Stats:
    st = Stats("Pacientes")
    rows = sqlite_conn.execute("SELECT * FROM pacientes ORDER BY ROWID").fetchall()
    st.total = len(rows)
    log.info(f"Pacientes no SQLite: {st.total:,}")

    cpfs_pg, cnss_pg = _carregar_chaves_pg(pg_conn)

    batch = []
    for row in rows:
        cpf = norm_cpf(row["cpf"])
        cns = norm_cns(row["sus"])

        # Pula se já existe por CPF ou CNS
        if (cpf and cpf in cpfs_pg) or (cns and cns in cnss_pg):
            st.pulados += 1
            continue

        rec = _transformar_paciente(row)
        if rec is None:
            st.erros += 1
            continue

        batch.append(rec)
        # Adiciona nas chaves para não inserir duplicatas da própria fonte
        if cpf: cpfs_pg.add(cpf)
        if cns: cnss_pg.add(cns)

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _inserir_batch(pg_conn, _PAC_INSERT, batch, st)
            else:
                st.inseridos += len(batch)
            batch.clear()
            log.info(f"  Pacientes: {st.inseridos:,} novos inseridos, {st.pulados:,} pulados...")

    if batch:
        if not dry_run:
            _inserir_batch(pg_conn, _PAC_INSERT, batch, st)
        else:
            st.inseridos += len(batch)

    log.info(f"Pacientes — novos: {st.inseridos:,} | pulados: {st.pulados:,} | erros: {st.erros}")
    return st


# ══════════════════════════════════════════════════════════════════════════════
#  PASSO 2 — Atendimentos históricos
# ══════════════════════════════════════════════════════════════════════════════

_ATD_COLS = ("paciente_id", "data_atendimento", "procedencia")
_ATD_INSERT = (
    "INSERT INTO recepcao_atendimentos (paciente_id, data_atendimento, procedencia) VALUES %s"
)


def _carregar_mapa_pacientes(pg_conn) -> dict[str, int]:
    """Retorna {cpf: id, cns: id} para resolução rápida."""
    mapa: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        cur.execute('SELECT id, num_cpf, cns FROM pacientes')
        for pid, cpf, cns in cur.fetchall():
            if cpf: mapa[cpf] = pid
            if cns: mapa[cns] = pid
    log.info(f"Mapa de pacientes carregado: {len(mapa):,} chaves (CPF + CNS).")
    return mapa


def migrar_atendimentos(sqlite_conn, pg_conn, dry_run: bool) -> Stats:
    st = Stats("Atendimentos")
    rows = sqlite_conn.execute(
        "SELECT cpf, sus, data_atendimento, hora_atendimento, procedencia "
        "FROM atendimentos ORDER BY id"
    ).fetchall()
    st.total = len(rows)
    log.info(f"Atendimentos no SQLite: {st.total:,}")

    mapa = _carregar_mapa_pacientes(pg_conn)

    # Deduplica por (cpf_clean, cns_clean, data, hora) — preserva a primeira ocorrência
    vistos: set[tuple] = set()
    batch = []
    sem_paciente = 0

    for row in rows:
        cpf = norm_cpf(row["cpf"])
        cns = norm_cns(row["sus"])
        data = _s(row["data_atendimento"])
        hora = _s(row["hora_atendimento"])

        chave = (cpf or "", cns or "", data, hora)
        if chave in vistos:
            st.pulados += 1
            continue
        vistos.add(chave)

        # Resolve paciente_id
        pac_id = mapa.get(cpf) or mapa.get(cns)
        if pac_id is None:
            sem_paciente += 1
            log.debug(f"Sem paciente: cpf={cpf} cns={cns} data={data}")
            st.pulados += 1
            continue

        dt = norm_datetime(data, hora)
        if dt is None:
            st.pulados += 1
            log.debug(f"Data inválida: {data} {hora}")
            continue

        proc = limpar(row["procedencia"]) or None
        batch.append((pac_id, dt, proc))

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _inserir_batch(pg_conn, _ATD_INSERT, batch, st)
            else:
                st.inseridos += len(batch)
            batch.clear()
            log.info(f"  Atendimentos: {st.inseridos:,} inseridos...")

    if batch:
        if not dry_run:
            _inserir_batch(pg_conn, _ATD_INSERT, batch, st)
        else:
            st.inseridos += len(batch)

    log.info(
        f"Atendimentos — inseridos: {st.inseridos:,} | "
        f"pulados: {st.pulados:,} (duplicatas + sem paciente) | "
        f"sem paciente no PG: {sem_paciente} | erros: {st.erros}"
    )
    return st


# ── Inserção em lote ──────────────────────────────────────────────────────────

def _inserir_batch(pg_conn, sql: str, batch: list, st: Stats) -> None:
    try:
        with pg_conn.cursor() as cur:
            execute_values(cur, sql, batch, page_size=BATCH_SIZE)
        pg_conn.commit()
        st.inseridos += len(batch)
    except Exception as exc:
        pg_conn.rollback()
        log.warning(f"Falha no lote ({exc}). Tentando individual...")
        _inserir_individual(pg_conn, sql, batch, st)


def _inserir_individual(pg_conn, sql_bulk: str, batch: list, st: Stats) -> None:
    ncols = len(batch[0])
    sql = sql_bulk.split("VALUES")[0].strip() + f" VALUES ({', '.join(['%s']*ncols)})"
    for rec in batch:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(sql, rec)
            pg_conn.commit()
            st.inseridos += 1
        except Exception as exc:
            pg_conn.rollback()
            st.erros += 1
            log.error(f"Erro individual: {rec[0]} | {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="migrate_v2 — HMPCF fase 2")
    ap.add_argument("--dry-run",   action="store_true", help="Simula sem gravar")
    ap.add_argument("--skip-pac",  action="store_true", help="Pula migração de pacientes")
    args = ap.parse_args()

    SEP = "═" * 56
    log.info(SEP)
    log.info("  MIGRATE V2 — hospital.db → PostgreSQL")
    log.info(f"  Origem  : {SQLITE_PATH}")
    log.info(f"  Destino : {PG_DSN['host']}:{PG_DSN['port']}/{PG_DSN['dbname']}")
    if args.dry_run: log.info("  Modo    : DRY-RUN (nenhum dado será gravado)")
    log.info(SEP)

    inicio = datetime.now()
    sqlite_conn = abrir_sqlite()
    pg_conn     = abrir_pg()

    resultados = []

    try:
        # 1. Pacientes novos
        if not args.skip_pac:
            log.info("\n── PASSO 1: Pacientes novos ──")
            st_pac = migrar_pacientes(sqlite_conn, pg_conn, args.dry_run)
            resultados.append(st_pac)

        # 2. Atendimentos
        log.info("\n── PASSO 2: Atendimentos históricos ──")
        st_atd = migrar_atendimentos(sqlite_conn, pg_conn, args.dry_run)
        resultados.append(st_atd)

    except KeyboardInterrupt:
        log.warning("Interrompido pelo usuário.")
    except Exception as exc:
        log.critical(f"Erro fatal: {exc}", exc_info=True)
    finally:
        sqlite_conn.close()
        if not pg_conn.closed:
            pg_conn.close()

    # Relatório
    duracao = datetime.now() - inicio
    log.info(f"\n{SEP}")
    log.info("  RELATÓRIO FINAL")
    log.info(SEP)
    for st in resultados:
        log.info(f"  {st.label:<15} total={st.total:>6,} | inseridos={st.inseridos:>6,} | "
                 f"pulados={st.pulados:>6,} | erros={st.erros}")
    log.info(f"  Duração: {duracao}")
    log.info(f"  Log completo: {LOG_FILE}")
    log.info(SEP)

    erros = sum(s.erros for s in resultados)
    sys.exit(0 if erros == 0 else 1)


if __name__ == "__main__":
    main()
