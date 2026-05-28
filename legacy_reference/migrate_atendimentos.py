#!/usr/bin/env python3
"""
migrate_atendimentos.py
=======================
ETL: tabela `atendimentos` do SQLite legado → `recepcao_atendimentos` no PostgreSQL.

O SQLite armazena CPF como "094.125.874-22" e CNS como "700 8059 6966 5085".
O PostgreSQL armazena apenas dígitos: "09412587422" e "700805969665085".

Para cada atendimento:
  1. Limpa CPF/SUS (remove pontuação/espaços)
  2. Busca `paciente_id` no PostgreSQL pelo CPF ou CNS
  3. Combina data + hora → datetime ISO
  4. Insere em recepcao_atendimentos (ignora duplicatas por (paciente_id, data_atendimento, registro))

USO:
    python migrate_atendimentos.py              # migração completa
    python migrate_atendimentos.py --dry-run    # simula sem gravar

CONFIGURAÇÃO (.env ou variáveis de ambiente):
    SQLITE_PATH, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
    POSTGRES_USER, POSTGRES_PASSWORD
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 nao instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    _env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env)
except ImportError:
    pass

# ── Configuração ──────────────────────────────────────────────────────────────

_BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
_SQLITE_DEFAULT = os.path.normpath(os.path.join(_BASE_DIR, "..", "hospital.db"))

SQLITE_PATH       = os.getenv("SQLITE_PATH",       _SQLITE_DEFAULT)
POSTGRES_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB",       "hmpcf")
POSTGRES_USER     = os.getenv("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "hmpcf2024")
BATCH_SIZE        = int(os.getenv("BATCH_SIZE",    "500"))
LOG_FILE          = os.path.join(_BASE_DIR, "migration_atendimentos.log")

# ── Logging ───────────────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("hmpcf.atendimentos")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    try:
        stdout_w = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", closefd=False)
    except Exception:
        stdout_w = sys.stdout
    ch = logging.StreamHandler(stdout_w)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

log = _setup_logging()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _so_digitos(v: str | None) -> str:
    """Remove tudo que não for dígito."""
    if not v:
        return ""
    return re.sub(r"\D", "", v)

def _parse_datetime(data: str | None, hora: str | None) -> datetime | None:
    """Combina 'YYYY-MM-DD' + 'HH:MM' em datetime. Retorna None se inválido."""
    if not data:
        return None
    try:
        data = data.strip()
        hora = (hora or "00:00").strip()
        if len(hora) == 5:
            return datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
        return datetime.strptime(data, "%Y-%m-%d")
    except ValueError:
        return None

def _parse_registro(v: str | None) -> int | None:
    """Converte texto '76' em inteiro 76. Retorna None se vazio/inválido ou fora do range SmallInteger."""
    if not v or not v.strip():
        return None
    try:
        n = int(v.strip())
        if -32768 <= n <= 32767:
            return n
        return None  # SmallInteger overflow — descarta
    except ValueError:
        return None

# ── Conexões ─────────────────────────────────────────────────────────────────

def conectar_sqlite() -> sqlite3.Connection:
    path = os.path.abspath(SQLITE_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQLite nao encontrado: {path}")
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    log.info("SQLite (read-only) => %s", path)
    return conn

def conectar_postgres() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        dbname=POSTGRES_DB, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    conn.autocommit = False
    log.info("PostgreSQL => %s:%s/%s (user=%s)", POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER)
    return conn

# ── Lógica principal ──────────────────────────────────────────────────────────

def carregar_mapa_pacientes(pg: psycopg2.extensions.connection) -> tuple[dict, dict]:
    """Retorna dois dicts: {cpf_digitos: id} e {cns_digitos: id}."""
    cur = pg.cursor()
    cur.execute("SELECT id, num_cpf, cns FROM pacientes")
    cpf_map: dict[str, int] = {}
    cns_map: dict[str, int] = {}
    for row in cur.fetchall():
        pid, cpf, cns = row
        if cpf:
            cpf_map[_so_digitos(cpf)] = pid
        if cns:
            cns_map[_so_digitos(cns)] = pid
    cur.close()
    log.info("Mapa de pacientes carregado: %d CPFs, %d CNSs", len(cpf_map), len(cns_map))
    return cpf_map, cns_map

def carregar_existentes(pg: psycopg2.extensions.connection) -> set[tuple]:
    """Carrega (paciente_id, data_atendimento truncada ao minuto) já inseridos."""
    cur = pg.cursor()
    cur.execute(
        "SELECT paciente_id, date_trunc('minute', data_atendimento) FROM recepcao_atendimentos"
    )
    existentes = {(row[0], row[1]) for row in cur.fetchall()}
    cur.close()
    log.info("Atendimentos ja existentes no PostgreSQL: %d", len(existentes))
    return existentes

def migrar(dry_run: bool = False) -> None:
    sqlite_conn = conectar_sqlite()
    pg_conn = conectar_postgres()

    try:
        cpf_map, cns_map = carregar_mapa_pacientes(pg_conn)
        existentes = carregar_existentes(pg_conn)

        cur_sqlite = sqlite_conn.cursor()
        cur_sqlite.execute("SELECT COUNT(*) FROM atendimentos")
        total_sqlite = cur_sqlite.fetchone()[0]
        log.info("Atendimentos no SQLite: %d", total_sqlite)

        cur_sqlite.execute(
            "SELECT id, cpf, sus, data_atendimento, hora_atendimento, registro, procedencia FROM atendimentos ORDER BY id"
        )

        batch: list[tuple] = []
        n_inseridos = 0
        n_pulados = 0
        n_sem_paciente = 0
        n_sem_data = 0

        def flush_batch():
            nonlocal n_inseridos
            if not batch or dry_run:
                if dry_run and batch:
                    log.info("[DRY-RUN] Simularia inserir %d atendimentos", len(batch))
                    n_inseridos += len(batch)
                batch.clear()
                return
            cur = pg_conn.cursor()
            execute_values(
                cur,
                """
                INSERT INTO recepcao_atendimentos
                    (paciente_id, data_atendimento, registro, procedencia, created_at, updated_at)
                VALUES %s
                """,
                batch,
            )
            pg_conn.commit()
            n_inseridos += cur.rowcount
            cur.close()
            batch.clear()

        for row in cur_sqlite:
            cpf_raw    = row["cpf"]
            sus_raw    = row["sus"]
            data_raw   = row["data_atendimento"]
            hora_raw   = row["hora_atendimento"]
            reg_raw    = row["registro"]
            proc_raw   = row["procedencia"]

            # Resolver paciente_id
            cpf_d = _so_digitos(cpf_raw)
            sus_d = _so_digitos(sus_raw)
            paciente_id = cpf_map.get(cpf_d) or cns_map.get(sus_d)

            if not paciente_id:
                n_sem_paciente += 1
                log.debug("Sem paciente: cpf=%s sus=%s — pulado", cpf_raw, sus_raw)
                continue

            # Resolver datetime
            dt = _parse_datetime(data_raw, hora_raw)
            if not dt:
                n_sem_data += 1
                log.debug("Data inválida: data=%s hora=%s — pulado", data_raw, hora_raw)
                continue

            # Verificar duplicata usando conjunto carregado em memória
            chave = (paciente_id, dt.replace(second=0, microsecond=0))
            if chave in existentes:
                n_pulados += 1
                continue
            existentes.add(chave)

            registro  = _parse_registro(reg_raw)
            procedencia = (proc_raw or "").strip() or None

            now = datetime.utcnow()
            batch.append((paciente_id, dt, registro, procedencia, now, now))

            if len(batch) >= BATCH_SIZE:
                flush_batch()
                log.info("  Progresso: %d inseridos, %d pulados, %d sem paciente...",
                         n_inseridos, n_pulados, n_sem_paciente)

        flush_batch()

        # ── Relatório final ───────────────────────────────────────────────────
        log.info("")
        log.info("=" * 58)
        log.info("  RELATORIO FINAL — ATENDIMENTOS")
        log.info("=" * 58)
        log.info("  Total SQLite      : %8d", total_sqlite)
        log.info("  Inseridos         : %8d%s", n_inseridos, "  (simulado)" if dry_run else "")
        log.info("  Pulados (dup)     : %8d", n_pulados)
        log.info("  Sem paciente (PG) : %8d", n_sem_paciente)
        log.info("  Data invalida     : %8d", n_sem_data)
        log.info("  STATUS            : %s", "CONCLUIDA" if not dry_run else "DRY-RUN OK")
        log.info("=" * 58)

    finally:
        sqlite_conn.close()
        pg_conn.close()


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Migra atendimentos do SQLite para PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar no PostgreSQL")
    args = parser.parse_args()

    if args.dry_run:
        log.info("=== DRY-RUN: nenhuma escrita no PostgreSQL ===")

    migrar(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
