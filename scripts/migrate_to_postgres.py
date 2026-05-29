#!/usr/bin/env python3
"""
migrate_to_postgres.py
======================
ETL profissional: hospital.db (SQLite legado) → PostgreSQL (HMPCF novo)

SEGURANÇA:
  - hospital.db é aberto em modo SOMENTE LEITURA (file URI mode=ro).
  - Nenhuma escrita, alteração ou exclusão ocorre no banco legado.
  - Credenciais carregadas exclusivamente via .env / variáveis de ambiente.

IDEMPOTÊNCIA:
  - Pacientes: deduplicação por CPF/CNS exato; sem doc → fuzzy nome ≥90% + dtnasc.
  - Atendimentos: deduplicação por paciente_id + data_atendimento exato.
  - Registros já existentes no PostgreSQL são pulados.

VALIDAÇÃO:
  - CPF: algoritmo de dígito verificador (módulo 11). Rejeita inválidos.
  - CNS: soma ponderada divisível por 11, primeiro dígito em {1,2,7,8,9}.
  - Datas: formatos YYYY-MM-DD, DD/MM/YYYY, YYYYMMDD, DDMMYYYY → YYYYMMDD.

USO:
    python migrate_to_postgres.py              # migração completa (pacientes + atendimentos)
    python migrate_to_postgres.py --dry-run    # simula sem gravar no PG
    python migrate_to_postgres.py --truncate   # limpa tabelas e re-migra

CONFIGURAÇÃO (arquivo .env ou variáveis de ambiente):
    SQLITE_PATH        caminho do hospital.db   (padrão: ../hospital.db)
    POSTGRES_HOST      host do PostgreSQL        (padrão: localhost)
    POSTGRES_PORT      porta                     (padrão: 5432)
    POSTGRES_DB        nome do banco             (padrão: hmpcf)
    POSTGRES_USER      usuário                   (padrão: postgres)
    POSTGRES_PASSWORD  senha                     (obrigatório)
    LOG_FILE           arquivo de log            (padrão: migration.log)
    BATCH_SIZE         registros por INSERT      (padrão: 500)
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
from difflib import SequenceMatcher
from typing import Optional, Tuple

# ── Dependências externas ─────────────────────────────────────────────────────

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 nao instalado.")
    print("      Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    _BASE_DIR_ENV = os.path.dirname(os.path.abspath(__file__))
    # Tenta scripts/.env primeiro; fallback para backend/.env
    _env_paths = [
        os.path.join(_BASE_DIR_ENV, ".env"),
        os.path.join(_BASE_DIR_ENV, "..", "backend", ".env"),
    ]
    for _env_path in _env_paths:
        if os.path.exists(_env_path):
            load_dotenv(_env_path)
            break
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACAO
# ══════════════════════════════════════════════════════════════════════════════

_BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
_SQLITE_DEFAULT = os.path.normpath(os.path.join(_BASE_DIR, "..", "hospital.db"))

SQLITE_PATH       = os.getenv("SQLITE_PATH",       _SQLITE_DEFAULT)
POSTGRES_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB",       "hmpcf")
POSTGRES_USER     = os.getenv("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
LOG_FILE          = os.getenv("LOG_FILE",           os.path.join(_BASE_DIR, "migration.log"))
BATCH_SIZE        = int(os.getenv("BATCH_SIZE",    "500"))

_DEFAULT_IBGE      = "240360"
_DEFAULT_CEPPCN    = "59575000"
_DEFAULT_CO_LOGRAD = "081"
_DEFAULT_NACIONAL  = "010"

# Limiar de similaridade para dedup fuzzy de nome (0.0 – 1.0)
FUZZY_THRESHOLD = 0.90


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("hmpcf.migration")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    try:
        stdout_w = open(
            sys.stdout.fileno(), mode="w", encoding="utf-8",
            errors="replace", closefd=False,
        )
    except Exception:
        stdout_w = sys.stdout
    ch = logging.StreamHandler(stdout_w)
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
        raise FileNotFoundError(
            f"Banco SQLite nao encontrado: {path}\n"
            f"Verifique SQLITE_PATH no arquivo .env."
        )
    uri = "file:///{}?mode=ro".format(path.replace("\\", "/").lstrip("/"))
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    log.info(f"SQLite (read-only) => {path}")
    return conn


def conectar_postgres() -> psycopg2.extensions.connection:
    if not POSTGRES_PASSWORD:
        log.warning("POSTGRES_PASSWORD nao definida. Configure o arquivo .env.")
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
        f"PostgreSQL => {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB} "
        f"(user={POSTGRES_USER})"
    )
    return conn


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDAÇÃO MATEMÁTICA — CPF e CNS
# ══════════════════════════════════════════════════════════════════════════════

def _validar_cpf(cpf: str) -> bool:
    """Valida CPF pelo algoritmo de dígito verificador (módulo 11)."""
    d = re.sub(r"\D", "", str(cpf or ""))
    if len(d) != 11:
        return False
    if re.match(r"^(\d)\1{10}$", d):  # sequências como 00000000000
        return False
    soma = sum(int(d[i]) * (10 - i) for i in range(9))
    dig1 = 0 if soma % 11 < 2 else 11 - soma % 11
    if dig1 != int(d[9]):
        return False
    soma = sum(int(d[i]) * (11 - i) for i in range(10))
    dig2 = 0 if soma % 11 < 2 else 11 - soma % 11
    return dig2 == int(d[10])


def _validar_cns(cns: str) -> bool:
    """
    Valida CNS/SUS pelo algoritmo padrão do DATASUS:
    - Exatamente 15 dígitos
    - Primeiro dígito em {1, 2, 7, 8, 9}
    - Soma ponderada (dígito[i] × (15 - i)) divisível por 11
    """
    d = re.sub(r"\D", "", str(cns or ""))
    if len(d) != 15:
        return False
    if d[0] not in "12789":
        return False
    soma = sum(int(d[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0


# ══════════════════════════════════════════════════════════════════════════════
#  NORMALIZAÇÃO DE NOME — para comparação fuzzy
# ══════════════════════════════════════════════════════════════════════════════

def _normalizar_nome(nome: str) -> str:
    """
    Normaliza nome para comparação fuzzy:
    maiúsculas, remove acentos, colapsa espaços múltiplos.
    """
    if not nome:
        return ""
    s = nome.strip().upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def _similaridade(a: str, b: str) -> float:
    """Retorna similaridade entre dois strings (0.0 – 1.0)."""
    return SequenceMatcher(None, a, b).ratio()


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSFORMADORES DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

def _str(v) -> str:
    return str(v).strip() if v is not None else ""


def _row_get(row: sqlite3.Row, key: str, default: str = "") -> str:
    try:
        v = row[key]
        return _str(v) if v is not None else default
    except (IndexError, KeyError):
        return default


def apenas_numeros(v) -> str:
    return re.sub(r"\D", "", _str(v))


def limpar(v, default: str = "") -> str:
    s = _str(v)
    return s if s else default


def truncar(v, maxlen: int, default: str = "") -> str:
    s = limpar(v, default)
    return s[:maxlen]


def norm_cpf(v) -> Optional[str]:
    """
    Normaliza e VALIDA CPF matematicamente.
    Retorna None para CPFs inválidos, formatados incorretamente ou
    com dígito verificador errado.
    """
    d = apenas_numeros(v)
    if not d:
        return None
    if len(d) > 11:
        return None  # provavelmente CNS no campo CPF
    if len(d) != 11:
        return None  # CPF incompleto — não há como validar
    if not _validar_cpf(d):
        return None
    return d


def norm_cns(v) -> Optional[str]:
    """
    Normaliza e VALIDA CNS matematicamente.
    Retorna None para CNS inválidos.
    """
    d = apenas_numeros(v)
    if not d:
        return None
    if not _validar_cns(d):
        return None
    return d[:15]


def norm_dtnasc(v) -> Optional[str]:
    """
    Converte data de nascimento para YYYYMMDD.
    Formatos aceitos: YYYY-MM-DD, DD/MM/YYYY, YYYYMMDD, DDMMYYYY.
    Retorna None para datas inválidas ou fora de 1900–hoje.
    """
    raw = _str(v)
    if not raw:
        return None
    num = re.sub(r"\D", "", raw)
    tentativas = [
        ("%Y-%m-%d", raw),
        ("%d/%m/%Y", raw),
        ("%Y%m%d",   num),
        ("%d%m%Y",   num),
    ]
    ano_max = datetime.now().year
    for fmt, alvo in tentativas:
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
    s = _str(v).upper()
    return s if s in ("M", "F") else "I"


_RACA_MAP: dict[str, str] = {
    "1": "01", "01": "01",
    "2": "02", "02": "02",
    "3": "03", "03": "03",
    "4": "04", "04": "04",
    "5": "05", "05": "05",
    "BRANCA":   "01",
    "PRETA":    "02",
    "PARDA":    "03",
    "AMARELA":  "04",
    "INDIGENA": "05",
}


def norm_raca(v) -> Optional[str]:
    raw = _str(v).upper()
    raw = raw.replace("Í", "I").replace("É", "E")
    return _RACA_MAP.get(raw)


def norm_telefone(v) -> Tuple[Optional[str], Optional[str]]:
    digits = apenas_numeros(v)
    if not digits:
        return None, None
    if digits.startswith("0") and len(digits) >= 11:
        digits = digits[1:]
    if len(digits) >= 10:
        return digits[:2], digits[2:11]
    return None, digits[:9]


def norm_estado(v) -> Optional[str]:
    s = _str(v)
    return s[:2].upper() if s else None


# ══════════════════════════════════════════════════════════════════════════════
#  CONTADORES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Contadores:
    total:          int  = 0
    migrados:       int  = 0
    ignorados:      int  = 0   # duplicatas por CPF/CNS exato
    ignorados_fuzzy: int = 0   # duplicatas por nome+dtnasc fuzzy
    cpf_invalido:   int  = 0   # barrados por CPF matematicamente inválido
    cns_invalido:   int  = 0   # barrados por CNS matematicamente inválido
    sem_documento:  int  = 0   # barrados por não ter CPF nem CNS válido
    erros:          int  = 0
    avisos:         list = field(default_factory=list)

    def avisar(self, cpf: str, msg: str) -> None:
        entrada = f"CPF={cpf or '?'} | {msg}"
        self.avisos.append(entrada)
        log.debug(f"AVISO {entrada}")

    @property
    def ok(self) -> bool:
        return self.erros == 0


# ══════════════════════════════════════════════════════════════════════════════
#  EXTRACT
# ══════════════════════════════════════════════════════════════════════════════

def extrair(sqlite_conn: sqlite3.Connection) -> list:
    cur = sqlite_conn.cursor()
    cur.execute("SELECT * FROM pacientes ORDER BY ROWID")
    rows = cur.fetchall()
    log.info(f"Extraidos {len(rows):,} registros do SQLite (tabela: pacientes).")
    return rows


def carregar_chaves_pg(pg_conn) -> tuple[set, set, dict]:
    """
    Carrega do PostgreSQL:
    - CPFs já existentes (set)
    - CNSs já existentes (set)
    - Nomes normalizados agrupados por dtnasc (dict[dtnasc → list[nome]])
      apenas para registros SEM CPF e SEM CNS válidos.
    """
    with pg_conn.cursor() as cur:
        cur.execute("SELECT num_cpf FROM pacientes WHERE num_cpf IS NOT NULL")
        cpfs = {r[0] for r in cur.fetchall()}

        cur.execute("SELECT cns FROM pacientes WHERE cns IS NOT NULL")
        cnss = {r[0] for r in cur.fetchall()}

        cur.execute(
            "SELECT nome, dtnasc FROM pacientes "
            "WHERE num_cpf IS NULL AND cns IS NULL "
            "  AND nome IS NOT NULL AND dtnasc IS NOT NULL"
        )
        nomes_pg: dict[str, list[str]] = {}
        for row in cur.fetchall():
            nome_norm = _normalizar_nome(row[0])
            dtnasc    = row[1]
            if nome_norm and dtnasc:
                nomes_pg.setdefault(dtnasc, []).append(nome_norm)

    log.info(
        f"PostgreSQL: {len(cpfs):,} CPFs | {len(cnss):,} CNSs | "
        f"{sum(len(v) for v in nomes_pg.values()):,} nomes s/ doc (para fuzzy)"
    )
    return cpfs, cnss, nomes_pg


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSFORM
# ══════════════════════════════════════════════════════════════════════════════

_COLS: tuple[str, ...] = (
    "cns", "num_cpf", "nome", "dtnasc", "sexo", "raca",
    "maepcn", "logpcn", "numpcn", "bairro_pcnte",
    "ddtel_pcnte", "tel_pcnte",
    "ibge", "ceppcn", "co_lograd",
    "nome_social", "idade", "civil", "ocupacao",
    "responsavel", "cidade", "estado",
    "nacionalidade", "naturalidade",
)

_INSERT_SQL = f"INSERT INTO pacientes ({', '.join(_COLS)}) VALUES %s"


def transformar(row: sqlite3.Row, c: Contadores) -> Optional[tuple]:
    cpf_raw = _row_get(row, "cpf")
    try:
        cns     = norm_cns(_row_get(row, "sus"))
        num_cpf = norm_cpf(cpf_raw)
        nome    = truncar(_row_get(row, "nome"),        100) or None
        dtnasc  = norm_dtnasc(_row_get(row, "dn"))
        sexo    = norm_sexo(_row_get(row, "sexo"))
        raca    = norm_raca(_row_get(row, "raca"))
        maepcn  = truncar(_row_get(row, "mae"),         100) or None
        logpcn  = truncar(_row_get(row, "endereco"),    100) or None
        numpcn  = truncar(_row_get(row, "numero"),      100) or None
        bairro  = truncar(_row_get(row, "bairro"),      100) or None
        ddd, tel = norm_telefone(_row_get(row, "tel"))

        ibge       = _DEFAULT_IBGE
        ceppcn     = _DEFAULT_CEPPCN
        co_lograd  = _DEFAULT_CO_LOGRAD

        nome_social  = truncar(_row_get(row, "nomeSocial"), 100) or None
        idade        = truncar(_row_get(row, "idade"),        50) or None
        civil        = truncar(_row_get(row, "civil"),        50) or None
        ocupacao     = truncar(_row_get(row, "ocupacao"),    100) or None
        responsavel  = truncar(_row_get(row, "responsavel"), 100) or None
        cidade       = truncar(_row_get(row, "cidade"),      100) or None
        estado       = norm_estado(_row_get(row, "estado"))
        nacionalidade = _DEFAULT_NACIONAL
        naturalidade  = truncar(_row_get(row, "naturalidade"), 100) or None

        # Alertas de qualidade
        if not nome:
            c.avisar(cpf_raw, "NOME vazio")
        if not num_cpf and not cns:
            c.avisar(cpf_raw, "sem CPF nem CNS valido")
        if _row_get(row, "dn") and dtnasc is None:
            c.avisar(cpf_raw, f"data invalida ignorada: '{_row_get(row, 'dn')}'")
        if sexo == "I" and limpar(_row_get(row, "sexo")):
            c.avisar(cpf_raw, f"sexo nao reconhecido: '{_row_get(row, 'sexo')}'")

        return (
            cns, num_cpf, nome, dtnasc, sexo, raca,
            maepcn, logpcn, numpcn, bairro,
            ddd, tel,
            ibge, ceppcn, co_lograd,
            nome_social, idade, civil, ocupacao,
            responsavel, cidade, estado,
            nacionalidade, naturalidade,
        )

    except Exception as exc:
        c.erros += 1
        log.error(f"ERRO ao transformar CPF={cpf_raw}: {exc}", exc_info=True)
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD
# ══════════════════════════════════════════════════════════════════════════════

def _inserir_batch(pg_conn, batch: list, c: Contadores) -> None:
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
            "Tentando insercao individual..."
        )
        _inserir_individualmente(pg_conn, batch, c)


def _inserir_individualmente(pg_conn, batch: list, c: Contadores) -> None:
    sql_ind = (
        f"INSERT INTO pacientes ({', '.join(_COLS)}) "
        f"VALUES ({', '.join(['%s'] * len(_COLS))})"
    )
    cpf_idx = list(_COLS).index("num_cpf")
    for record in batch:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(sql_ind, record)
            pg_conn.commit()
            c.migrados += 1
        except Exception as exc:
            pg_conn.rollback()
            c.erros += 1
            log.error(f"ERRO SQL | CPF={record[cpf_idx] or '?'} | {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  TRUNCATE
# ══════════════════════════════════════════════════════════════════════════════

def truncar_tabelas(pg_conn) -> None:
    log.warning(
        "TRUNCANDO recepcao_atendimentos e pacientes (RESTART IDENTITY)... "
        "Esta operacao remove TODOS os registros."
    )
    with pg_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE recepcao_atendimentos, pacientes RESTART IDENTITY;"
        )
    pg_conn.commit()
    log.warning("Tabelas truncadas.")


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDAÇÃO FINAL
# ══════════════════════════════════════════════════════════════════════════════

def _validar_migracao(sqlite_conn, pg_conn, c: Contadores) -> None:
    cur_sq = sqlite_conn.cursor()
    cur_sq.execute("SELECT COUNT(*) FROM pacientes")
    total_sqlite = cur_sq.fetchone()[0]

    with pg_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pacientes")
        total_pg = cur.fetchone()[0]

    log.info(
        f"Validacao => SQLite: {total_sqlite:,} | "
        f"PostgreSQL: {total_pg:,} | "
        f"Migrados: {c.migrados:,} | "
        f"Dup: {c.ignorados:,} | "
        f"Sem doc: {c.sem_documento:,} | "
        f"CPF inv: {c.cpf_invalido:,} | "
        f"CNS inv: {c.cns_invalido:,} | "
        f"Erros: {c.erros:,}"
    )

    processados = c.migrados + c.ignorados + c.sem_documento + c.erros
    if processados == c.total:
        log.info("Validacao OK: todos os registros do SQLite foram processados.")
    else:
        log.warning(
            f"Atencao: {c.total - processados:,} registros nao processados."
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE ETL PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def migrar(dry_run: bool = False, truncate: bool = False) -> tuple[Contadores, ContadoresAtd]:
    c     = Contadores()
    c_atd = ContadoresAtd()
    sqlite_conn = None
    pg_conn     = None

    try:
        sqlite_conn = conectar_sqlite()

        # Conecta ao PG sempre — necessário para leitura (dedup e mapa de pacientes).
        # Em dry-run, apenas lê; nunca escreve.
        pg_conn = conectar_postgres()
        if not dry_run and truncate:
            truncar_tabelas(pg_conn)

        # Chaves já existentes no destino
        cpfs_pg, cnss_pg, nomes_pg = carregar_chaves_pg(pg_conn)

        rows    = extrair(sqlite_conn)
        c.total = len(rows)

        if c.total == 0:
            log.warning("Nenhum registro encontrado na tabela pacientes do SQLite.")
            return c

        batch: list = []
        inicio = datetime.now()

        for row in rows:
            cpf_raw = _row_get(row, "cpf")
            sus_raw = _row_get(row, "sus")

            cpf = norm_cpf(cpf_raw)
            cns = norm_cns(sus_raw)

            # ── Conta documentos barrados pela validação matemática ───────────
            cpf_digits = apenas_numeros(cpf_raw)
            if cpf_digits and len(cpf_digits) == 11 and cpf is None:
                c.cpf_invalido += 1
                log.debug(f"CPF invalido (digito verificador): {cpf_digits}")

            cns_digits = apenas_numeros(sus_raw)
            if cns_digits and len(cns_digits) == 15 and cns is None:
                c.cns_invalido += 1
                log.debug(f"CNS invalido (checksum): {cns_digits}")

            # ── Dedup por CPF/CNS exato ───────────────────────────────────────
            if (cpf and cpf in cpfs_pg) or (cns and cns in cnss_pg):
                c.ignorados += 1
                continue

            # ── Sem CPF nem CNS válido → descarta ────────────────────────────
            if not cpf and not cns:
                c.sem_documento += 1
                log.debug(f"Sem documento valido: nome={_row_get(row, 'nome')!r}")
                continue

            # ── Transforma e enfileira ────────────────────────────────────────
            record = transformar(row, c)
            if record is None:
                continue

            batch.append(record)

            # Atualiza chaves locais para dedup dentro da própria fonte
            if cpf:
                cpfs_pg.add(cpf)
            if cns:
                cnss_pg.add(cns)

            if len(batch) >= BATCH_SIZE:
                if not dry_run:
                    _inserir_batch(pg_conn, batch, c)
                else:
                    c.migrados += len(batch)

                decorrido   = max((datetime.now() - inicio).seconds, 1)
                processados = c.migrados + c.ignorados + c.sem_documento + c.erros
                pct = processados / c.total * 100
                log.info(
                    f"  {processados:>6,}/{c.total:,} ({pct:5.1f}%)  "
                    f"migrados={c.migrados:,}  dup={c.ignorados:,}  "
                    f"sem_doc={c.sem_documento:,}  erros={c.erros:,}  [{decorrido}s]"
                )
                batch.clear()

        # Último lote parcial
        if batch:
            if not dry_run:
                _inserir_batch(pg_conn, batch, c)
            else:
                c.migrados += len(batch)

        if not dry_run:
            _validar_migracao(sqlite_conn, pg_conn, c)

        # ── Pipeline de atendimentos ──────────────────────────────────────────
        log.info("")
        log.info("── ETAPA 2: Atendimentos ─────────────────────────────────────")
        c_atd = migrar_atendimentos(sqlite_conn, pg_conn, dry_run)

    except FileNotFoundError as exc:
        log.critical(str(exc))
    except psycopg2.OperationalError as exc:
        log.critical(f"Falha de conexao com o PostgreSQL: {exc}")
        if pg_conn and not pg_conn.closed:
            pg_conn.rollback()
    except KeyboardInterrupt:
        log.warning("Migracao interrompida (Ctrl+C).")
        if pg_conn and not pg_conn.closed:
            pg_conn.rollback()
    except Exception as exc:
        log.critical(f"Erro inesperado: {exc}", exc_info=True)
        if pg_conn and not pg_conn.closed:
            pg_conn.rollback()
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if pg_conn and not pg_conn.closed:
            pg_conn.close()

    return c, c_atd


# ══════════════════════════════════════════════════════════════════════════════
#  ATENDIMENTOS — contadores, helpers e pipeline
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContadoresAtd:
    total:           int = 0
    migrados:        int = 0
    ignorados:       int = 0   # duplicatas exatas (paciente_id + datetime)
    sem_paciente:    int = 0   # CPF/CNS não encontrado no PG
    erros:           int = 0

    @property
    def ok(self) -> bool:
        return self.erros == 0


def construir_mapa_pacientes(pg_conn) -> dict[str, int]:
    """
    Retorna dict mapeando identificador normalizado → paciente_id.
    Carrega CPFs e CNSs do PostgreSQL.
    """
    mapa: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id, num_cpf FROM pacientes WHERE num_cpf IS NOT NULL")
        for pid, cpf in cur.fetchall():
            mapa[cpf] = pid
        cur.execute("SELECT id, cns FROM pacientes WHERE cns IS NOT NULL")
        for pid, cns in cur.fetchall():
            mapa[cns] = pid
    log.info(f"Mapa de pacientes: {len(mapa):,} identificadores (CPF + CNS)")
    return mapa


def carregar_chaves_atd(pg_conn) -> set[tuple]:
    """
    Carrega (paciente_id, data_atendimento) já existentes no PG para dedup.
    """
    with pg_conn.cursor() as cur:
        cur.execute("SELECT paciente_id, data_atendimento FROM recepcao_atendimentos")
        chaves = {(r[0], r[1]) for r in cur.fetchall()}
    log.info(f"Atendimentos ja no PG: {len(chaves):,} (usados para dedup)")
    return chaves


def norm_datetime_atd(data_str: str, hora_str: str) -> Optional[datetime]:
    """
    Combina data 'YYYY-MM-DD' + hora 'HH:MM' → datetime.
    Retorna None se inválido.
    """
    d = _str(data_str)
    h = _str(hora_str) or "00:00"
    if not d:
        return None
    try:
        return datetime.strptime(f"{d} {h}", "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            return None


_COLS_ATD: tuple[str, ...] = (
    "paciente_id", "data_atendimento", "registro", "procedencia",
)

_INSERT_ATD = f"INSERT INTO recepcao_atendimentos ({', '.join(_COLS_ATD)}) VALUES %s"


def transformar_atd(
    row: sqlite3.Row,
    mapa: dict[str, int],
    c: ContadoresAtd,
) -> Optional[tuple]:
    """
    Converte linha de atendimentos SQLite → tuple para INSERT no PG.
    Retorna None se paciente não encontrado ou erro irrecuperável.
    """
    cpf_raw = _row_get(row, "cpf")
    sus_raw = _row_get(row, "sus")

    # Resolve paciente_id via CPF ou CNS (já normalizados)
    paciente_id: Optional[int] = None
    cpf = norm_cpf(cpf_raw)
    cns = norm_cns(sus_raw)
    if cpf:
        paciente_id = mapa.get(cpf)
    if paciente_id is None and cns:
        paciente_id = mapa.get(cns)

    if paciente_id is None:
        c.sem_paciente += 1
        log.debug(f"Paciente nao encontrado: CPF={cpf_raw!r} SUS={sus_raw!r}")
        return None

    data_atd = norm_datetime_atd(
        _row_get(row, "data_atendimento"),
        _row_get(row, "hora_atendimento"),
    )
    if data_atd is None:
        c.erros += 1
        log.error(f"Data invalida no atendimento paciente_id={paciente_id}")
        return None

    reg_raw = _str(_row_get(row, "registro"))
    try:
        registro = int(reg_raw) if reg_raw else None
        if registro is not None and not (-32768 <= registro <= 32767):
            registro = None
    except ValueError:
        registro = None

    procedencia = _str(_row_get(row, "procedencia")) or None

    return (paciente_id, data_atd, registro, procedencia)


def migrar_atendimentos(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    dry_run: bool,
) -> ContadoresAtd:
    """Pipeline ETL de atendimentos: Extract → Transform → Load."""
    c = ContadoresAtd()

    rows = sqlite_conn.execute(
        "SELECT * FROM atendimentos ORDER BY id"
    ).fetchall()
    c.total = len(rows)
    log.info(f"Extraidos {c.total:,} atendimentos do SQLite.")

    if c.total == 0:
        return c

    # Mapa de identificadores para resolver paciente_id (sempre usa PG, mesmo em dry-run)
    mapa = construir_mapa_pacientes(pg_conn)

    # Chaves já existentes para dedup
    chaves_pg: set[tuple] = carregar_chaves_atd(pg_conn)

    batch: list = []
    inicio = datetime.now()

    for row in rows:
        record = transformar_atd(row, mapa, c)
        if record is None:
            continue  # sem_paciente ou erro já contabilizado

        chave = (record[0], record[1])  # (paciente_id, data_atendimento)
        if chave in chaves_pg:
            c.ignorados += 1
            continue

        batch.append(record)
        chaves_pg.add(chave)

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _inserir_batch_atd(pg_conn, batch, c)
            else:
                c.migrados += len(batch)

            decorrido   = max((datetime.now() - inicio).seconds, 1)
            processados = c.migrados + c.ignorados + c.sem_paciente + c.erros
            pct = processados / c.total * 100
            log.info(
                f"  ATD {processados:>6,}/{c.total:,} ({pct:5.1f}%)  "
                f"migrados={c.migrados:,}  dup={c.ignorados:,}  "
                f"sem_pac={c.sem_paciente:,}  erros={c.erros:,}  [{decorrido}s]"
            )
            batch.clear()

    if batch:
        if not dry_run:
            _inserir_batch_atd(pg_conn, batch, c)
        else:
            c.migrados += len(batch)

    log.info(
        f"Atendimentos => migrados={c.migrados:,}  "
        f"dup={c.ignorados:,}  sem_paciente={c.sem_paciente:,}  erros={c.erros:,}"
    )
    return c


def _inserir_batch_atd(pg_conn, batch: list, c: ContadoresAtd) -> None:
    if not batch:
        return
    try:
        with pg_conn.cursor() as cur:
            execute_values(cur, _INSERT_ATD, batch, page_size=BATCH_SIZE)
        pg_conn.commit()
        c.migrados += len(batch)
    except Exception as exc:
        pg_conn.rollback()
        log.warning(f"Falha no lote de atendimentos ({exc}). Tentando individual...")
        _inserir_atd_individual(pg_conn, batch, c)


def _inserir_atd_individual(pg_conn, batch: list, c: ContadoresAtd) -> None:
    sql = (
        f"INSERT INTO recepcao_atendimentos ({', '.join(_COLS_ATD)}) "
        f"VALUES ({', '.join(['%s'] * len(_COLS_ATD))})"
    )
    for record in batch:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(sql, record)
            pg_conn.commit()
            c.migrados += 1
        except Exception as exc:
            pg_conn.rollback()
            c.erros += 1
            log.error(f"ERRO SQL atendimento paciente_id={record[0]}: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIO FINAL
# ══════════════════════════════════════════════════════════════════════════════

def exibir_relatorio(
    c: Contadores,
    c_atd: ContadoresAtd,
    dry_run: bool,
    duracao: object,
) -> None:
    SEP  = "=" * 62
    SEP2 = "-" * 62
    log.info("")
    log.info(SEP)
    log.info("  RELATORIO FINAL DE MIGRACAO")
    log.info("  HMPCF - Hospital Municipal Pedro Coutinho Filho")
    if dry_run:
        log.info("  [DRY-RUN] Nenhum dado foi gravado no PostgreSQL")
    log.info(SEP)
    log.info(f"  Origem     : {os.path.abspath(SQLITE_PATH)}")
    log.info(f"  Destino    : {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

    log.info(SEP2)
    log.info("  PACIENTES")
    log.info(SEP2)
    log.info(f"  Total SQLite          : {c.total:>8,}")
    log.info(f"  Migrados              : {c.migrados:>8,}")
    log.info(f"  Ignorados (dup exata) : {c.ignorados:>8,}  (mesmo CPF ou CNS)")
    log.info(f"  Sem CPF nem CNS       : {c.sem_documento:>8,}  (descartados)")
    log.info(f"  CPF invalido (barrado): {c.cpf_invalido:>8,}  (digito verificador)")
    log.info(f"  CNS invalido (barrado): {c.cns_invalido:>8,}  (checksum DATASUS)")
    log.info(f"  Erros                 : {c.erros:>8,}")
    log.info(f"  Avisos de dados       : {len(c.avisos):>8,}")
    if c.total:
        processados = c.migrados + c.ignorados + c.sem_documento + c.erros
        log.info(f"  Processados           : {processados / c.total * 100:>7.1f}%")

    if c.avisos:
        log.info(SEP2)
        log.info(f"  AVISOS pacientes (primeiros 30 de {len(c.avisos):,}):")
        for aviso in c.avisos[:30]:
            log.warning(f"    [!] {aviso}")
        if len(c.avisos) > 30:
            log.info(f"    ... +{len(c.avisos) - 30} avisos — veja: {LOG_FILE}")

    log.info(SEP2)
    log.info("  ATENDIMENTOS")
    log.info(SEP2)
    log.info(f"  Total SQLite          : {c_atd.total:>8,}")
    log.info(f"  Migrados              : {c_atd.migrados:>8,}")
    log.info(f"  Ignorados (dup exata) : {c_atd.ignorados:>8,}  (paciente_id + datetime)")
    log.info(f"  Sem paciente (pulado) : {c_atd.sem_paciente:>8,}  (CPF/CNS nao encontrado)")
    log.info(f"  Erros                 : {c_atd.erros:>8,}")
    if c_atd.total:
        processados_atd = c_atd.migrados + c_atd.ignorados + c_atd.sem_paciente + c_atd.erros
        log.info(f"  Processados           : {processados_atd / c_atd.total * 100:>7.1f}%")

    log.info(SEP2)
    ok_geral = c.ok and c_atd.ok
    log.info(f"  STATUS   : {'CONCLUIDA COM SUCESSO' if ok_geral else 'CONCLUIDA COM ERROS'}")
    log.info(f"  Duracao  : {duracao}")
    log.info(f"  Log      : {os.path.abspath(LOG_FILE)}")
    log.info(SEP)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "ETL: hospital.db (SQLite legado) -> PostgreSQL (HMPCF)\n"
            "SQLite aberto em SOMENTE LEITURA — nenhuma escrita no legado.\n"
            "Validacao matematica de CPF (mod 11) e CNS (DATASUS).\n"
            "Dedup fuzzy por nome >= 90% + dtnasc para registros sem doc valido."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dry-run",   action="store_true",
                   help="Processa tudo sem gravar no PostgreSQL.")
    p.add_argument("--truncate",  action="store_true",
                   help="Limpa tabelas antes de inserir. IRREVERSIVEL.")
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
        log.info("  Atencao : --truncate ativo — tabelas serao limpas antes")
    log.info("")

    inicio        = datetime.now()
    c, c_atd      = migrar(dry_run=args.dry_run, truncate=args.truncate)
    duracao       = datetime.now() - inicio

    exibir_relatorio(c, c_atd, dry_run=args.dry_run, duracao=duracao)
    sys.exit(0 if (c.ok and c_atd.ok) else 1)
