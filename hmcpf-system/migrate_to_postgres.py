#!/usr/bin/env python3
"""
migrate_to_postgres.py
======================
ETL: hospital.db (SQLite, tabela pacientes) → PostgreSQL

Padrão de destino: Firebird/CADCNS + campos extras do sistema legado HMPCF.

Uso:
    python migrate_to_postgres.py             # migração completa
    python migrate_to_postgres.py --dry-run   # simula sem gravar no PG
    python migrate_to_postgres.py --truncate  # limpa tabela antes de migrar

Requerimentos:
    pip install psycopg2-binary python-dotenv
"""

import os
import re
import sys
import sqlite3
import logging
import argparse
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Tuple

# ── Dependências opcionais ────────────────────────────────────────────────────

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 não instalado.")
    print("      Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # .env é opcional


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
#  Edite aqui ou use variáveis de ambiente / arquivo .env
# ══════════════════════════════════════════════════════════════════════════════

# hospital.db fica na raiz do projeto (um nível acima de hmcpf-system/)
_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_SQLITE_DEFAULT = os.path.join(_BASE_DIR, "..", "hospital.db")

SQLITE_PATH       = os.getenv("SQLITE_PATH",       _SQLITE_DEFAULT)
POSTGRES_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB",       "hmpcf")
POSTGRES_USER     = os.getenv("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
LOG_FILE          = os.getenv("LOG_FILE",           "migration.log")
BATCH_SIZE        = int(os.getenv("BATCH_SIZE",    "500"))


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING — arquivo completo + console resumido
# ══════════════════════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("migration")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = _setup_logging()


# ══════════════════════════════════════════════════════════════════════════════
#  CONEXÕES
# ══════════════════════════════════════════════════════════════════════════════

def conectar_sqlite() -> sqlite3.Connection:
    """Abre conexão somente leitura no SQLite."""
    path = os.path.abspath(SQLITE_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Banco SQLite não encontrado: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    log.info(f"SQLite   → {path}")
    return conn


def conectar_postgres() -> psycopg2.extensions.connection:
    """Abre conexão com o PostgreSQL."""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=10,
    )
    conn.autocommit = False
    log.info(
        f"PostgreSQL → {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB} "
        f"(user={POSTGRES_USER})"
    )
    return conn


# ══════════════════════════════════════════════════════════════════════════════
#  FUNÇÕES DE LIMPEZA E TRANSFORMAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def _str(v) -> str:
    """Converte qualquer valor para string segura, nunca lança exceção."""
    return str(v).strip() if v is not None else ""


def apenas_numeros(v) -> str:
    """Remove tudo que não for dígito numérico."""
    return re.sub(r"\D", "", _str(v))


def limpar_texto(v, default: str = "") -> str:
    """Retorna texto limpo ou `default` quando vazio/nulo."""
    s = _str(v)
    return s if s else default


def transformar_data(v) -> Optional[str]:
    """
    Normaliza datas para o formato YYYYMMDD (padrão CADCNS).

    Formatos aceitos:
      YYYY-MM-DD  →  20010130
      DD/MM/YYYY  →  20010130
      YYYYMMDD    →  (já correto)
      DDMMYYYY    →  20010130

    Retorna None para datas inválidas — nunca levanta exceção.
    """
    raw = _str(v)
    if not raw:
        return None

    tentativas = [
        ("%Y-%m-%d", raw),
        ("%d/%m/%Y", raw),
        ("%Y%m%d",   apenas_numeros(raw)),
        ("%d%m%Y",   apenas_numeros(raw)),
    ]

    ano_atual = datetime.now().year

    for fmt, alvo in tentativas:
        if len(alvo) not in (8, 10):
            continue
        try:
            dt = datetime.strptime(alvo, fmt)
            if not (1900 <= dt.year <= ano_atual):
                continue
            return dt.strftime("%Y%m%d")
        except ValueError:
            continue

    return None


def transformar_sexo(v) -> str:
    """Aceita M ou F; qualquer outro valor retorna I (indefinido)."""
    s = _str(v).upper()
    return s if s in ("M", "F") else "I"


# Mapeamento raça: código numérico ou texto → código CADCNS 2 dígitos
_RACA_MAP: dict[str, str] = {
    "1": "01", "01": "01",   # Branca
    "2": "02", "02": "02",   # Preta
    "3": "03", "03": "03",   # Parda
    "4": "04", "04": "04",   # Amarela
    "5": "05", "05": "05",   # Indígena
    "BRANCA":   "01",
    "PRETA":    "02",
    "PARDA":    "03",
    "AMARELA":  "04",
    "INDIGENA": "05",
    "INDÍGENA": "05",
}


def transformar_raca(v) -> Optional[str]:
    """Normaliza raça para código CADCNS de 2 dígitos. None se não reconhecido."""
    return _RACA_MAP.get(_str(v).upper())


def transformar_telefone(v) -> Tuple[Optional[str], Optional[str]]:
    """
    Separa DDD e número a partir de qualquer formato de telefone.

    Exemplos:
      (84)999999999  →  ('84', '999999999')
      84999999999    →  ('84', '999999999')
      999999999      →  (None, '999999999')

    Retorna (None, None) se o valor for vazio ou inválido.
    Nunca lança IndexError.
    """
    digits = apenas_numeros(v)
    if not digits:
        return None, None

    # Remove zero de DDDs antigos tipo "084..."
    if digits.startswith("0") and len(digits) >= 11:
        digits = digits[1:]

    if len(digits) >= 10:
        ddd    = digits[:2]
        numero = digits[2:14]   # máx. 12 dígitos
        return ddd, numero

    # Número sem DDD identificável
    return None, digits[:12]


# ══════════════════════════════════════════════════════════════════════════════
#  CONTADORES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Contadores:
    total:     int  = 0
    migrados:  int  = 0
    ignorados: int  = 0
    erros:     int  = 0
    avisos:    list = field(default_factory=list)

    def avisar(self, cpf: str, msg: str) -> None:
        entrada = f"CPF={cpf or '?'} | {msg}"
        self.avisos.append(entrada)
        log.debug(f"AVISO {entrada}")


# ══════════════════════════════════════════════════════════════════════════════
#  DDL — CRIAÇÃO DA TABELA E ÍNDICES
# ══════════════════════════════════════════════════════════════════════════════

_DDL_TABELA = """
CREATE TABLE IF NOT EXISTS pacientes (
    id             BIGSERIAL    PRIMARY KEY,

    -- ── Padrão Firebird / CADCNS ──────────────────────────────────────────
    "CNS"          TEXT,
    "NUM_CPF"      VARCHAR(11),
    "NOME"         TEXT,
    "DTNASC"       VARCHAR(8),       -- YYYYMMDD
    "SEXO"         CHAR(1),          -- M | F | I
    "RACA"         VARCHAR(2),       -- 01..05 (SIGTAP/CADCNS)
    "MAEPCN"       TEXT,
    "LOGPCN"       TEXT   NOT NULL DEFAULT 'principal',
    "NUMPCN"       TEXT   NOT NULL DEFAULT 's/n',
    "BAIRRO_PCNTE" TEXT   NOT NULL DEFAULT 'centro',
    "NMRES"        TEXT,             -- naturalidade / município de residência
    "DDTEL_PCNTE"  VARCHAR(3),
    "TEL_PCNTE"    VARCHAR(12),

    -- ── Campos extras do sistema legado HMPCF ─────────────────────────────
    "nomeSocial"   TEXT,
    "idade"        TEXT,
    "civil"        TEXT,
    "ocupacao"     TEXT,
    "responsavel"  TEXT,
    "cidade"       TEXT,
    "estado"       VARCHAR(2),

    -- ── Metadados de migração ──────────────────────────────────────────────
    migrated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""

_DDL_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_pac_cpf  ON pacientes ("NUM_CPF");',
    'CREATE INDEX IF NOT EXISTS idx_pac_cns  ON pacientes ("CNS");',
    'CREATE INDEX IF NOT EXISTS idx_pac_nome ON pacientes ("NOME");',
]


def criar_tabela(pg_conn) -> None:
    """Cria tabela e índices no PostgreSQL (idempotente)."""
    with pg_conn.cursor() as cur:
        cur.execute(_DDL_TABELA)
        for ddl in _DDL_INDEXES:
            cur.execute(ddl)
    pg_conn.commit()
    log.info("Tabela e índices verificados/criados.")


def truncar_tabela(pg_conn) -> None:
    """Remove todos os registros e reinicia a sequência do id."""
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE pacientes RESTART IDENTITY;")
    pg_conn.commit()
    log.warning("Tabela truncada — registros anteriores removidos.")


# ══════════════════════════════════════════════════════════════════════════════
#  EXTRACT — leitura do SQLite
# ══════════════════════════════════════════════════════════════════════════════

def extrair(sqlite_conn: sqlite3.Connection) -> list:
    """Lê todos os registros da tabela pacientes no SQLite."""
    cur = sqlite_conn.cursor()
    cur.execute("SELECT * FROM pacientes ORDER BY ROWID")
    rows = cur.fetchall()
    log.info(f"Extraídos {len(rows):,} registros do SQLite.")
    return rows


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSFORM — conversão de cada linha
# ══════════════════════════════════════════════════════════════════════════════

# Colunas na ordem exata do INSERT
_COLUNAS = (
    '"CNS"', '"NUM_CPF"', '"NOME"', '"DTNASC"', '"SEXO"', '"RACA"',
    '"MAEPCN"', '"LOGPCN"', '"NUMPCN"', '"BAIRRO_PCNTE"', '"NMRES"',
    '"DDTEL_PCNTE"', '"TEL_PCNTE"',
    '"nomeSocial"', '"idade"', '"civil"', '"ocupacao"',
    '"responsavel"', '"cidade"', '"estado"',
)


def transformar(row: sqlite3.Row, c: Contadores) -> Optional[tuple]:
    """
    Converte uma linha do SQLite em tuple para INSERT no PostgreSQL.

    Nunca lança exceção — registra aviso e retorna None em caso de falha grave.
    """
    cpf_raw = _str(row["cpf"])

    try:
        cns     = apenas_numeros(row["sus"])  or None
        num_cpf = apenas_numeros(cpf_raw)     or None
        nome    = limpar_texto(row["nome"])   or None
        dtnasc  = transformar_data(row["dn"])
        sexo    = transformar_sexo(row["sexo"])
        raca    = transformar_raca(row["raca"])
        maepcn  = limpar_texto(row["mae"])    or None
        logpcn  = limpar_texto(row["endereco"], default="principal")
        numpcn  = limpar_texto(row["numero"],   default="s/n")
        bairro  = limpar_texto(row["bairro"],   default="centro")
        nmres   = limpar_texto(row["naturalidade"]) or None
        ddd, tel = transformar_telefone(row["tel"])

        nome_social = limpar_texto(row["nomeSocial"])  or None
        idade       = limpar_texto(row["idade"])        or None
        civil       = limpar_texto(row["civil"])        or None
        ocupacao    = limpar_texto(row["ocupacao"])     or None
        responsavel = limpar_texto(row["responsavel"])  or None
        cidade      = limpar_texto(row["cidade"])       or None
        estado_raw  = limpar_texto(row["estado"])
        estado      = estado_raw[:2].upper() if estado_raw else None

        # ── Alertas de qualidade de dados ────────────────────────────────
        if not nome:
            c.avisar(cpf_raw, "NOME vazio")
        if not num_cpf and not cns:
            c.avisar(cpf_raw, "sem CPF nem CNS")
        if row["dn"] and dtnasc is None:
            c.avisar(cpf_raw, f"data inválida ignorada: '{row['dn']}'")
        if sexo == "I" and limpar_texto(row["sexo"]):
            c.avisar(cpf_raw, f"sexo não reconhecido: '{row['sexo']}'")
        if raca is None and limpar_texto(row["raca"]):
            c.avisar(cpf_raw, f"raça não reconhecida: '{row['raca']}'")

        return (
            cns, num_cpf, nome, dtnasc, sexo, raca,
            maepcn, logpcn, numpcn, bairro, nmres,
            ddd, tel,
            nome_social, idade, civil, ocupacao,
            responsavel, cidade, estado,
        )

    except Exception as exc:
        c.erros += 1
        log.error(f"ERRO ao transformar CPF={cpf_raw}: {exc}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD — inserção em lote no PostgreSQL
# ══════════════════════════════════════════════════════════════════════════════

_INSERT_SQL = (
    f"INSERT INTO pacientes ({', '.join(_COLUNAS)}) VALUES %s"
)


def _inserir_batch(pg_conn, batch: list, c: Contadores) -> None:
    """
    Insere um lote de registros via execute_values (bulk).
    Em caso de falha, faz fallback linha-a-linha para isolar o problema.
    """
    if not batch:
        return
    try:
        with pg_conn.cursor() as cur:
            execute_values(cur, _INSERT_SQL, batch, page_size=BATCH_SIZE)
        pg_conn.commit()
        c.migrados += len(batch)

    except Exception as exc:
        pg_conn.rollback()
        log.warning(
            f"Falha no lote de {len(batch)} registros ({exc}). "
            "Tentando inserção individual para isolar o erro..."
        )
        _inserir_individualmente(pg_conn, batch, c)


def _inserir_individualmente(pg_conn, batch: list, c: Contadores) -> None:
    """Fallback: insere registro por registro — identifica exatamente qual falha."""
    sql_individual = (
        f"INSERT INTO pacientes ({', '.join(_COLUNAS)}) "
        f"VALUES ({', '.join(['%s'] * len(_COLUNAS))})"
    )
    cpf_idx = list(_COLUNAS).index('"NUM_CPF"')

    for record in batch:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(sql_individual, record)
            pg_conn.commit()
            c.migrados += 1
        except Exception as exc:
            pg_conn.rollback()
            c.erros += 1
            cpf_id = record[cpf_idx] if record[cpf_idx] else "?"
            log.error(f"ERRO SQL | CPF={cpf_id} | {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL — ETL completo
# ══════════════════════════════════════════════════════════════════════════════

def migrar(dry_run: bool = False, truncate: bool = False) -> Contadores:
    """
    Orquestra o pipeline Extract → Transform → Load.

    dry_run  : executa tudo sem gravar nada no PostgreSQL.
    truncate : limpa a tabela antes de inserir.
    """
    c = Contadores()
    sqlite_conn = None
    pg_conn     = None

    try:
        sqlite_conn = conectar_sqlite()

        if not dry_run:
            pg_conn = conectar_postgres()
            criar_tabela(pg_conn)
            if truncate:
                truncar_tabela(pg_conn)

        # ── Extract ───────────────────────────────────────────────────────
        rows    = extrair(sqlite_conn)
        c.total = len(rows)

        if c.total == 0:
            log.warning("Nenhum registro encontrado no SQLite.")
            return c

        # ── Transform + Load ──────────────────────────────────────────────
        batch:   list  = []
        inicio = datetime.now()

        for i, row in enumerate(rows, start=1):
            record = transformar(row, c)

            if record is None:
                c.ignorados += 1
                continue

            batch.append(record)

            if len(batch) >= BATCH_SIZE:
                if pg_conn:
                    _inserir_batch(pg_conn, batch, c)
                else:
                    c.migrados += len(batch)   # dry-run: conta sem gravar

                decorrido = (datetime.now() - inicio).seconds
                pct       = c.migrados / c.total * 100
                log.info(
                    f"  {c.migrados:>6,}/{c.total:,} migrados "
                    f"({pct:5.1f}%)  —  {decorrido}s"
                )
                batch.clear()

        # Último lote parcial
        if batch:
            if pg_conn:
                _inserir_batch(pg_conn, batch, c)
            else:
                c.migrados += len(batch)

    except FileNotFoundError as exc:
        log.critical(str(exc))
    except psycopg2.OperationalError as exc:
        log.critical(f"Falha de conexão PostgreSQL: {exc}")
    except KeyboardInterrupt:
        log.warning("Migração interrompida pelo usuário (Ctrl+C).")
    except Exception as exc:
        log.critical(f"Erro inesperado: {exc}", exc_info=True)
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if pg_conn and not pg_conn.closed:
            pg_conn.close()

    return c


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIO FINAL
# ══════════════════════════════════════════════════════════════════════════════

def exibir_relatorio(c: Contadores, dry_run: bool) -> None:
    sep  = "═" * 54
    sep2 = "─" * 54

    log.info("")
    log.info(sep)
    log.info("  RELATÓRIO FINAL DE MIGRAÇÃO")
    if dry_run:
        log.info("  ⚠  MODO DRY-RUN — nenhum dado foi gravado")
    log.info(sep)
    log.info(f"  Total extraído   : {c.total:>8,}")
    log.info(f"  Migrados         : {c.migrados:>8,}")
    log.info(f"  Ignorados        : {c.ignorados:>8,}")
    log.info(f"  Erros            : {c.erros:>8,}")
    log.info(f"  Avisos de dados  : {len(c.avisos):>8,}")

    if c.total:
        pct = c.migrados / c.total * 100
        log.info(f"  Taxa de sucesso  : {pct:>7.1f}%")

    if c.avisos:
        log.info(sep2)
        log.info(f"  AVISOS (primeiros 30 de {len(c.avisos):,}):")
        for aviso in c.avisos[:30]:
            log.warning(f"    ⚠  {aviso}")
        if len(c.avisos) > 30:
            log.info(f"    ... +{len(c.avisos) - 30} avisos — veja {LOG_FILE}")

    log.info(sep2)
    status = "CONCLUÍDA COM SUCESSO" if c.erros == 0 else "CONCLUÍDA COM ERROS"
    log.info(f"  STATUS : {status}")
    log.info(f"  Log    : {os.path.abspath(LOG_FILE)}")
    log.info(sep)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Migração SQLite → PostgreSQL — HMPCF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python migrate_to_postgres.py\n"
            "  python migrate_to_postgres.py --dry-run\n"
            "  python migrate_to_postgres.py --truncate\n"
        ),
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Executa o ETL completo sem gravar nada no PostgreSQL.",
    )
    p.add_argument(
        "--truncate", action="store_true",
        help="Limpa a tabela pacientes antes de inserir (permite re-execução).",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _args()

    log.info("═" * 54)
    log.info("  MIGRAÇÃO SQLite → PostgreSQL")
    log.info("  HMPCF — Hospital Municipal Pedro Coutinho Filho")
    log.info("═" * 54)
    log.info(f"  Origem  : {os.path.abspath(SQLITE_PATH)}")
    log.info(f"  Destino : {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    log.info(f"  Lote    : {BATCH_SIZE} registros")
    if args.dry_run:
        log.info("  Modo    : DRY-RUN (sem gravação)")
    if args.truncate:
        log.info("  Atenção : --truncate ativo")
    log.info("")

    inicio   = datetime.now()
    c        = migrar(dry_run=args.dry_run, truncate=args.truncate)
    duracao  = datetime.now() - inicio

    exibir_relatorio(c, dry_run=args.dry_run)
    log.info(f"  Duração total : {duracao}")

    sys.exit(0 if c.erros == 0 else 1)
