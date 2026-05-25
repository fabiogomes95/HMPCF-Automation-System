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
  - Deduplicação por CPF e CNS antes de cada inserção.
  - Registros já existentes no PostgreSQL são pulados com aviso.

USO:
    python migrate_to_postgres.py              # migração completa
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
from dataclasses import dataclass, field
from datetime import datetime
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
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv e opcional — recomendado mas nao obrigatorio


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACAO
#  Edite o arquivo .env — nunca coloque credenciais no codigo.
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

# Defaults obrigatorios — campos NOT NULL no modelo PostgreSQL (HMPCF/BPA)
_DEFAULT_LOGPCN    = "PRINCIPAL"   # logpcn  — logradouro vazio
_DEFAULT_NUMPCN    = "S/N"         # numpcn  — numero vazio
_DEFAULT_BAIRRO    = "CENTRO"      # bairro_pcnte
_DEFAULT_IBGE      = "240360"      # ibge    — codigo IBGE Extremoz/RN
_DEFAULT_CEPPCN    = "59575000"    # ceppcn
_DEFAULT_CO_LOGRAD = "081"         # co_lograd — tipo de logradouro "RUA"
_DEFAULT_NACIONAL  = "010"         # nacionalidade — Brasileiro


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING — arquivo completo (DEBUG) + console resumido (INFO)
# ══════════════════════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("hmpcf.migration")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de arquivo — captura tudo (DEBUG+)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Handler de console — UTF-8 com fallback para Windows
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
    """
    Abre o hospital.db em modo SOMENTE LEITURA via URI SQLite.
    Qualquer tentativa de escrita lancara OperationalError.
    """
    path = os.path.abspath(SQLITE_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Banco SQLite nao encontrado: {path}\n"
            f"Verifique SQLITE_PATH no arquivo .env."
        )

    # file:///caminho?mode=ro => read-only; nao cria arquivo se nao existir
    uri = "file:///{}?mode=ro".format(path.replace("\\", "/").lstrip("/"))
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    log.info(f"SQLite (read-only) => {path}")
    return conn


def conectar_postgres() -> psycopg2.extensions.connection:
    """Abre conexao com o PostgreSQL com autocommit desabilitado."""
    if not POSTGRES_PASSWORD:
        log.warning(
            "POSTGRES_PASSWORD nao definida. "
            "Configure o arquivo .env com a senha do banco."
        )
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
#  TRANSFORMADORES DE DADOS
#  Cada funcao e autonoma, nunca lanca excecao para chamadores.
# ══════════════════════════════════════════════════════════════════════════════

def _str(v) -> str:
    """Converte qualquer valor para string segura. None => ''."""
    return str(v).strip() if v is not None else ""


def _row_get(row: sqlite3.Row, key: str, default: str = "") -> str:
    """Acesso seguro a coluna do sqlite3.Row — nao falha se coluna nao existe."""
    try:
        v = row[key]
        return _str(v) if v is not None else default
    except (IndexError, KeyError):
        return default


def apenas_numeros(v) -> str:
    """Remove todos os caracteres nao-numericos."""
    return re.sub(r"\D", "", _str(v))


def limpar(v, default: str = "") -> str:
    """Retorna string limpa ou `default` quando vazia/nula."""
    s = _str(v)
    return s if s else default


def truncar(v, maxlen: int, default: str = "") -> str:
    """String limpa truncada em `maxlen`. None ou vazio => `default`."""
    s = limpar(v, default)
    return s[:maxlen]


def norm_cpf(v) -> Optional[str]:
    """
    Normaliza CPF: remove nao-digitos.
    Rejeita se >11 digitos (provavel CNS inserido no campo CPF).
    Rejeita se <8 digitos (dado insuficiente para identificacao).
    """
    d = apenas_numeros(v)
    if not d:
        return None
    if len(d) > 11:
        return None  # CNS ou dado invalido no campo CPF
    return d if len(d) >= 8 else None


def norm_cns(v) -> Optional[str]:
    """Normaliza CNS: remove nao-digitos, limita a 15 caracteres."""
    d = apenas_numeros(v)
    return d[:15] if d else None


def norm_dtnasc(v) -> Optional[str]:
    """
    Converte data de nascimento para YYYYMMDD (padrao CADCNS/BPA).

    Formatos aceitos:
      YYYY-MM-DD  (ISO)
      DD/MM/YYYY  (BR)
      YYYYMMDD    (ja no formato correto)
      DDMMYYYY    (numerico BR)

    Retorna None para datas invalidas ou fora do intervalo 1900–hoje.
    Nunca lanca excecao.
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
    """Aceita M ou F; qualquer outro valor retorna I (indefinido)."""
    s = _str(v).upper()
    return s if s in ("M", "F") else "I"


_RACA_MAP: dict[str, str] = {
    # Codigos numericos
    "1": "01", "01": "01",
    "2": "02", "02": "02",
    "3": "03", "03": "03",
    "4": "04", "04": "04",
    "5": "05", "05": "05",
    # Descricoes textuais
    "BRANCA":   "01",
    "PRETA":    "02",
    "PARDA":    "03",
    "AMARELA":  "04",
    "INDIGENA": "05",
    "INDIGENA": "05",  # com acento normalizado
}


def norm_raca(v) -> Optional[str]:
    """Normaliza raca para codigo CADCNS (01-05). None se nao reconhecido."""
    raw = _str(v).upper()
    # Normaliza acentuacao basica
    raw = raw.replace("Í", "I").replace("é", "e")  # I-agudo, e-agudo
    return _RACA_MAP.get(raw)


def norm_telefone(v) -> Tuple[Optional[str], Optional[str]]:
    """
    Separa DDD (2 digitos) e numero (ate 9 digitos) a partir de qualquer
    formato de telefone brasileiro.

    Exemplos:
      (84) 99999-9999  =>  ('84', '999999999')
      84999999999      =>  ('84', '999999999')
      84-3333-3333     =>  ('84', '33333333')
      999999999        =>  (None, '999999999')

    Retorna (None, None) se vazio.
    Nunca lanca IndexError.
    """
    digits = apenas_numeros(v)
    if not digits:
        return None, None

    # Remove zero inicial de DDDs antigos como "084..."
    if digits.startswith("0") and len(digits) >= 11:
        digits = digits[1:]

    if len(digits) >= 10:
        return digits[:2], digits[2:11]  # DDD 2 digitos + tel ate 9 digitos

    return None, digits[:9]


def norm_estado(v) -> Optional[str]:
    """Normaliza UF para 2 letras maiusculas. None se vazio."""
    s = _str(v)
    return s[:2].upper() if s else None


# ══════════════════════════════════════════════════════════════════════════════
#  CONTADORES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Contadores:
    total:     int  = 0   # registros lidos do SQLite
    migrados:  int  = 0   # inseridos com sucesso no PostgreSQL
    ignorados: int  = 0   # pulados por duplicidade (CPF ou CNS ja existia)
    erros:     int  = 0   # falhas de transformacao ou erro SQL
    avisos:    list = field(default_factory=list)  # alertas de qualidade de dados

    def avisar(self, cpf: str, msg: str) -> None:
        entrada = f"CPF={cpf or '?'} | {msg}"
        self.avisos.append(entrada)
        log.debug(f"AVISO {entrada}")

    @property
    def ok(self) -> bool:
        return self.erros == 0


# ══════════════════════════════════════════════════════════════════════════════
#  EXTRACT — leitura somente leitura do SQLite
# ══════════════════════════════════════════════════════════════════════════════

def extrair(sqlite_conn: sqlite3.Connection) -> list:
    """Le todos os registros da tabela pacientes no SQLite (somente leitura)."""
    cur = sqlite_conn.cursor()
    cur.execute("SELECT * FROM pacientes ORDER BY ROWID")
    rows = cur.fetchall()
    log.info(f"Extraidos {len(rows):,} registros do SQLite (tabela: pacientes).")
    return rows


def carregar_chaves_pg(pg_conn) -> tuple[set, set]:
    """
    Carrega CPFs e CNSs ja existentes no PostgreSQL para deduplicacao.
    Retorna (cpfs: set, cnss: set).
    """
    with pg_conn.cursor() as cur:
        cur.execute("SELECT num_cpf FROM pacientes WHERE num_cpf IS NOT NULL")
        cpfs = {r[0] for r in cur.fetchall()}

        cur.execute("SELECT cns FROM pacientes WHERE cns IS NOT NULL")
        cnss = {r[0] for r in cur.fetchall()}

    log.info(
        f"PostgreSQL: {len(cpfs):,} CPFs e {len(cnss):,} CNSs ja existentes "
        f"(usados para deduplicacao)."
    )
    return cpfs, cnss


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSFORM — mapeamento SQLite -> PostgreSQL
#
#  Mapeamento de colunas:
#    sus          => cns          (remove nao-digitos)
#    cpf          => num_cpf      (remove nao-digitos, max 11)
#    nome         => nome
#    dn           => dtnasc       (converte para YYYYMMDD)
#    sexo         => sexo         (M/F ou I)
#    raca         => raca         (01..05)
#    mae          => maepcn
#    endereco     => logpcn       (default: PRINCIPAL)
#    numero       => numpcn       (default: S/N)
#    bairro       => bairro_pcnte (default: CENTRO)
#    naturalidade => nmres + naturalidade
#    tel          => ddtel_pcnte + tel_pcnte (separa DDD)
#    nomeSocial   => nome_social
#    idade        => idade
#    civil        => civil
#    ocupacao     => ocupacao
#    responsavel  => responsavel
#    cidade       => cidade
#    estado       => estado
#
#  Campos novos (sem equivalente no SQLite — usam defaults BPA):
#    ibge         => "240390"  (Extremoz/RN)
#    ceppcn       => "59575000"
#    co_lograd    => "081"     (RUA)
#    nacionalidade => "010"    (Brasileiro)
# ══════════════════════════════════════════════════════════════════════════════

# Colunas na ordem exata usada no INSERT — deve espelhar o modelo Paciente
_COLS: tuple[str, ...] = (
    "cns", "num_cpf", "nome", "dtnasc", "sexo", "raca",
    "maepcn", "logpcn", "numpcn", "bairro_pcnte", "nmres",
    "ddtel_pcnte", "tel_pcnte",
    "ibge", "ceppcn", "co_lograd",
    "nome_social", "idade", "civil", "ocupacao",
    "responsavel", "cidade", "estado",
    "nacionalidade", "naturalidade",
)

_INSERT_SQL = f"INSERT INTO pacientes ({', '.join(_COLS)}) VALUES %s"


def transformar(row: sqlite3.Row, c: Contadores) -> Optional[tuple]:
    """
    Converte uma linha do SQLite em tuple para INSERT no PostgreSQL.

    Nunca lanca excecao — registra aviso/erro em `c` e retorna None se
    a transformacao falhar de forma irrecuperavel.
    """
    cpf_raw = _row_get(row, "cpf")

    try:
        cns     = norm_cns(_row_get(row, "sus"))
        num_cpf = norm_cpf(cpf_raw)
        nome    = truncar(_row_get(row, "nome"),        100) or None
        dtnasc  = norm_dtnasc(_row_get(row, "dn"))
        sexo    = norm_sexo(_row_get(row, "sexo"))
        raca    = norm_raca(_row_get(row, "raca"))
        maepcn  = truncar(_row_get(row, "mae"),         100) or None
        logpcn  = truncar(_row_get(row, "endereco"),    100, default=_DEFAULT_LOGPCN)
        numpcn  = truncar(_row_get(row, "numero"),      100, default=_DEFAULT_NUMPCN)
        bairro  = truncar(_row_get(row, "bairro"),      100, default=_DEFAULT_BAIRRO)
        nmres   = truncar(_row_get(row, "naturalidade"), 100) or None
        ddd, tel = norm_telefone(_row_get(row, "tel"))

        # Campos BPA sem equivalente no SQLite — defaults obrigatorios
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

        # ── Alertas de qualidade de dados ────────────────────────────────────
        if not nome:
            c.avisar(cpf_raw, "NOME vazio")
        if not num_cpf and not cns:
            c.avisar(cpf_raw, "sem CPF nem CNS — registro nao identificavel")
        if _row_get(row, "dn") and dtnasc is None:
            c.avisar(cpf_raw, f"data invalida ignorada: '{_row_get(row, 'dn')}'")
        if sexo == "I" and limpar(_row_get(row, "sexo")):
            c.avisar(cpf_raw, f"sexo nao reconhecido: '{_row_get(row, 'sexo')}'")
        if raca is None and limpar(_row_get(row, "raca")):
            c.avisar(cpf_raw, f"raca nao reconhecida: '{_row_get(row, 'raca')}'")

        return (
            cns, num_cpf, nome, dtnasc, sexo, raca,
            maepcn, logpcn, numpcn, bairro, nmres,
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
#  LOAD — insercao em lote no PostgreSQL
# ══════════════════════════════════════════════════════════════════════════════

def _inserir_batch(pg_conn, batch: list, c: Contadores) -> None:
    """
    Insere um lote de registros via execute_values (bulk insert).
    Em caso de falha do lote, faz rollback e tenta individualmente
    para isolar o registro problematico.
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
            "Tentando insercao individual para isolar o erro..."
        )
        _inserir_individualmente(pg_conn, batch, c)


def _inserir_individualmente(pg_conn, batch: list, c: Contadores) -> None:
    """
    Fallback: insere registro por registro.
    Permite identificar exatamente qual registro causa o erro SQL.
    """
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
            cpf_id = record[cpf_idx] or "?"
            log.error(f"ERRO SQL | CPF={cpf_id} | {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  TRUNCATE — limpa tabelas antes de re-migracao
# ══════════════════════════════════════════════════════════════════════════════

def truncar_tabelas(pg_conn) -> None:
    """
    Remove todos os registros de recepcao_atendimentos e pacientes
    e reinicia as sequencias de ID.

    ATENCAO: operacao irreversivel — use apenas em ambiente de desenvolvimento
    ou quando houver backup confirmado.
    """
    log.warning(
        "TRUNCANDO recepcao_atendimentos e pacientes (RESTART IDENTITY)... "
        "Esta operacao remove TODOS os registros das duas tabelas."
    )
    with pg_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE recepcao_atendimentos, pacientes RESTART IDENTITY;"
        )
    pg_conn.commit()
    log.warning("Tabelas truncadas. Todos os registros foram removidos.")


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDACAO — contagem SQLite vs PostgreSQL
# ══════════════════════════════════════════════════════════════════════════════

def validar(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    c: Contadores,
) -> None:
    """
    Compara a contagem de registros no SQLite com o total no PostgreSQL
    apos a migracao e registra um relatorio de validacao.
    """
    cur_sq = sqlite_conn.cursor()
    cur_sq.execute("SELECT COUNT(*) FROM pacientes")
    total_sqlite = cur_sq.fetchone()[0]

    with pg_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pacientes")
        total_pg = cur.fetchone()[0]

    log.info(
        f"Validacao => SQLite: {total_sqlite:,} registros | "
        f"PostgreSQL: {total_pg:,} total | "
        f"Migrados nesta execucao: {c.migrados:,} | "
        f"Pulados (dup): {c.ignorados:,} | "
        f"Erros: {c.erros:,}"
    )

    processados = c.migrados + c.ignorados + c.erros
    if processados == c.total:
        log.info("Validacao OK: todos os registros do SQLite foram processados.")
    else:
        log.warning(
            f"Validacao: {c.total - processados:,} registros do SQLite "
            f"nao foram processados."
        )

    if total_sqlite > total_pg:
        faltando = total_sqlite - total_pg
        log.warning(
            f"ATENCAO: {faltando:,} registros do SQLite nao estao no PostgreSQL. "
            f"Verifique erros e duplicatas no log: {LOG_FILE}"
        )
    else:
        excedente = total_pg - total_sqlite
        if excedente:
            log.info(
                f"PostgreSQL contem {excedente:,} registros a mais que o SQLite "
                f"(possivelmente de outras fontes ou execucoes anteriores)."
            )
        else:
            log.info(
                "Validacao perfeita: PostgreSQL contem exatamente os mesmos "
                "registros que o SQLite."
            )


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE ETL PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def migrar(dry_run: bool = False, truncate: bool = False) -> Contadores:
    """
    Orquestra o pipeline completo: Extract => Transform => Load.

    dry_run  : processa tudo sem gravar nada no PostgreSQL.
    truncate : limpa pacientes e atendimentos antes de inserir.
    """
    c = Contadores()
    sqlite_conn: Optional[sqlite3.Connection] = None
    pg_conn     = None

    try:
        # ── Conexoes ──────────────────────────────────────────────────────────
        sqlite_conn = conectar_sqlite()

        if not dry_run:
            pg_conn = conectar_postgres()
            if truncate:
                truncar_tabelas(pg_conn)

        # ── Deduplicacao: chaves ja existentes no destino ─────────────────────
        cpfs_pg: set[str] = set()
        cnss_pg: set[str] = set()
        if pg_conn:
            cpfs_pg, cnss_pg = carregar_chaves_pg(pg_conn)

        # ── Extract ───────────────────────────────────────────────────────────
        rows    = extrair(sqlite_conn)
        c.total = len(rows)

        if c.total == 0:
            log.warning("Nenhum registro encontrado na tabela pacientes do SQLite.")
            return c

        # ── Transform + Load ──────────────────────────────────────────────────
        batch: list = []
        inicio = datetime.now()

        for row in rows:
            cpf = norm_cpf(_row_get(row, "cpf"))
            cns = norm_cns(_row_get(row, "sus"))

            # Pula se CPF ou CNS ja existem no PostgreSQL ou nesta execucao
            if (cpf and cpf in cpfs_pg) or (cns and cns in cnss_pg):
                c.ignorados += 1
                continue

            record = transformar(row, c)
            if record is None:
                # Erro ja contabilizado em c.erros dentro de transformar()
                continue

            batch.append(record)

            # Registra nas chaves locais para evitar duplicatas dentro da fonte
            if cpf:
                cpfs_pg.add(cpf)
            if cns:
                cnss_pg.add(cns)

            if len(batch) >= BATCH_SIZE:
                if pg_conn:
                    _inserir_batch(pg_conn, batch, c)
                else:
                    c.migrados += len(batch)  # dry-run: conta sem gravar

                decorrido = max((datetime.now() - inicio).seconds, 1)
                processados = c.migrados + c.ignorados + c.erros
                pct = processados / c.total * 100
                log.info(
                    f"  {processados:>6,}/{c.total:,} processados "
                    f"({pct:5.1f}%)  |  migrados={c.migrados:,}  "
                    f"pulados={c.ignorados:,}  erros={c.erros:,}  "
                    f"[{decorrido}s]"
                )
                batch.clear()

        # Ultimo lote parcial
        if batch:
            if pg_conn:
                _inserir_batch(pg_conn, batch, c)
            else:
                c.migrados += len(batch)

        # ── Validacao final ───────────────────────────────────────────────────
        if pg_conn:
            validar(sqlite_conn, pg_conn, c)

    except FileNotFoundError as exc:
        log.critical(str(exc))
    except psycopg2.OperationalError as exc:
        log.critical(f"Falha de conexao com o PostgreSQL: {exc}")
        if pg_conn and not pg_conn.closed:
            pg_conn.rollback()
    except KeyboardInterrupt:
        log.warning("Migracao interrompida pelo usuario (Ctrl+C).")
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

    return c


# ══════════════════════════════════════════════════════════════════════════════
#  RELATORIO FINAL
# ══════════════════════════════════════════════════════════════════════════════

def exibir_relatorio(
    c: Contadores,
    dry_run: bool,
    duracao: object,
) -> None:
    SEP  = "=" * 58
    SEP2 = "-" * 58

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
    log.info(f"  Total SQLite     : {c.total:>8,}")
    log.info(f"  Migrados         : {c.migrados:>8,}")
    log.info(f"  Ignorados (dup)  : {c.ignorados:>8,}")
    log.info(f"  Erros            : {c.erros:>8,}")
    log.info(f"  Avisos de dados  : {len(c.avisos):>8,}")

    if c.total:
        processados = c.migrados + c.ignorados + c.erros
        pct = processados / c.total * 100
        log.info(f"  Processados      : {pct:>7.1f}%")

    if c.avisos:
        log.info(SEP2)
        log.info(f"  AVISOS (primeiros 30 de {len(c.avisos):,} total):")
        for aviso in c.avisos[:30]:
            log.warning(f"    [!] {aviso}")
        if len(c.avisos) > 30:
            log.info(
                f"    ... +{len(c.avisos) - 30} avisos — "
                f"veja o arquivo: {LOG_FILE}"
            )

    log.info(SEP2)
    status = "CONCLUIDA COM SUCESSO" if c.ok else "CONCLUIDA COM ERROS"
    log.info(f"  STATUS   : {status}")
    log.info(f"  Duracao  : {duracao}")
    log.info(f"  Log      : {os.path.abspath(LOG_FILE)}")
    log.info(SEP)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "ETL profissional: hospital.db (SQLite legado) -> PostgreSQL (HMPCF)\n"
            "O SQLite e aberto em modo SOMENTE LEITURA — nenhuma escrita no legado."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python migrate_to_postgres.py\n"
            "  python migrate_to_postgres.py --dry-run\n"
            "  python migrate_to_postgres.py --truncate\n\n"
            "Configuracao via arquivo .env ou variaveis de ambiente:\n"
            "  SQLITE_PATH, POSTGRES_HOST, POSTGRES_PORT,\n"
            "  POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD,\n"
            "  LOG_FILE, BATCH_SIZE\n"
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Processa o ETL completo (extrai, transforma, valida) "
            "sem gravar nada no PostgreSQL."
        ),
    )
    p.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "Limpa as tabelas pacientes e recepcao_atendimentos antes de "
            "inserir. Permite re-execucao limpa. IRREVERSIVEL."
        ),
    )
    return p.parse_args()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = _parse_args()

    SEP = "=" * 58
    log.info(SEP)
    log.info("  MIGRACAO SQLite => PostgreSQL")
    log.info("  HMPCF - Hospital Municipal Pedro Coutinho Filho")
    log.info(SEP)
    log.info(f"  Origem  : {os.path.abspath(SQLITE_PATH)}")
    log.info(f"  Destino : {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    log.info(f"  Lote    : {BATCH_SIZE} registros por INSERT em lote")
    log.info(f"  Log     : {os.path.abspath(LOG_FILE)}")

    if args.dry_run:
        log.info("  Modo    : DRY-RUN (nenhum dado sera gravado)")
    if args.truncate:
        log.info("  Atencao : --truncate ativo — tabelas serao limpas antes")

    log.info("")

    inicio  = datetime.now()
    c       = migrar(dry_run=args.dry_run, truncate=args.truncate)
    duracao = datetime.now() - inicio

    exibir_relatorio(c, dry_run=args.dry_run, duracao=duracao)
    sys.exit(0 if c.ok else 1)
