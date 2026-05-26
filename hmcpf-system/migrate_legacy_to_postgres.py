#!/usr/bin/env python3
"""
migrate_legacy_to_postgres.py
=============================
Migração OFICIAL do banco legado SQLite → PostgreSQL HMPCF
Hospital Municipal Pedro Coutinho Filho — Extremoz/RN

REGRAS ABSOLUTAS
----------------
  • SQLite original: SOMENTE LEITURA — jamais escrito, jamais apagado
  • Backup automático com timestamp antes de qualquer operação
  • Idempotente: seguro para executar quantas vezes for necessário
  • Rollback transacional em caso de falha crítica

USO
---
  python migrate_legacy_to_postgres.py              # migração completa
  python migrate_legacy_to_postgres.py --dry-run    # simula, sem gravar
  python migrate_legacy_to_postgres.py --skip-backup  # pula backup (use com cautela)

CONFIGURAÇÃO (.env ou variáveis de ambiente)
--------------------------------------------
  SQLITE_PATH        caminho do hospital.db   (padrão: ../hospital.db)
  POSTGRES_HOST      host PostgreSQL           (padrão: localhost)
  POSTGRES_PORT      porta PostgreSQL          (padrão: 5432)
  POSTGRES_DB        banco                     (padrão: hmpcf)
  POSTGRES_USER      usuário                   (padrão: postgres)
  POSTGRES_PASSWORD  senha                     (obrigatório)
  BACKUP_DIR         pasta de backups          (padrão: ./backup)
  LOG_FILE           arquivo de log            (padrão: migration_official.log)
  BATCH_SIZE         registros por batch       (padrão: 500)
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERRO: psycopg2 nao instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

_BASE = Path(__file__).parent

SQLITE_PATH       = Path(os.getenv("SQLITE_PATH",      str(_BASE / ".." / "hospital.db"))).resolve()
POSTGRES_HOST     = os.getenv("POSTGRES_HOST",          "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT",      "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB",            "hmpcf")
POSTGRES_USER     = os.getenv("POSTGRES_USER",          "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD",      "hmpcf2024")
BACKUP_DIR        = Path(os.getenv("BACKUP_DIR",        str(_BASE / "backup")))
LOG_FILE          = Path(os.getenv("LOG_FILE",          str(_BASE / "migration_official.log")))
BATCH_SIZE        = int(os.getenv("BATCH_SIZE",         "500"))

# Defaults para campos NOT NULL no modelo PostgreSQL
_DEFAULT_LOGPCN    = None
_DEFAULT_NUMPCN    = None
_DEFAULT_BAIRRO    = None
_DEFAULT_IBGE      = "240360"   # Extremoz/RN
_DEFAULT_CEP       = "59575000"
_DEFAULT_LOGRAD    = "081"
_DEFAULT_NACIONAL  = "010"      # Brasileiro
_DEFAULT_DTNASC    = "19900101"

_RACA_MAP = {
    "BRANCA": "01", "BRANCO": "01",
    "PRETA":  "02", "PRETO":  "02", "NEGRO": "02", "NEGRA": "02",
    "PARDA":  "03", "PARDO":  "03", "MORENA": "03", "MORENO": "03",
    "AMARELA":"04", "AMARELO":"04",
    "INDIGENA":"05","INDÍGENA":"05","INDIO":"05","ÍNDIO":"05",
}

# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("hmpcf.migration_oficial")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    try:
        stdout_w = open(sys.stdout.fileno(), "w", encoding="utf-8",
                        errors="replace", closefd=False)
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
#  CONTADORES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Counters:
    pac_total_sqlite:     int = 0
    pac_validos:          int = 0
    pac_ignorados_invalidos: int = 0
    pac_ignorados_semid:  int = 0
    pac_duplicatas_fundidas: int = 0
    pac_inseridos:        int = 0
    pac_ja_existiam:      int = 0
    pac_datas_corrigidas: int = 0
    atd_total_sqlite:     int = 0
    atd_migrados:         int = 0
    atd_duplicatas:       int = 0
    atd_sem_paciente:     int = 0
    atd_data_invalida:    int = 0

# ══════════════════════════════════════════════════════════════════════════════
#  BACKUP
# ══════════════════════════════════════════════════════════════════════════════

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def fazer_backup(skip: bool = False) -> Path:
    if skip:
        log.warning("Backup ignorado por --skip-backup. Use com cautela.")
        return SQLITE_PATH

    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"SQLite nao encontrado: {SQLITE_PATH}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    destino = BACKUP_DIR / f"hospital_{ts}.db"

    log.info("Criando backup: %s", destino)
    shutil.copy2(SQLITE_PATH, destino)

    orig_size  = SQLITE_PATH.stat().st_size
    bkp_size   = destino.stat().st_size
    orig_hash  = _sha256(SQLITE_PATH)
    bkp_hash   = _sha256(destino)

    if orig_size != bkp_size or orig_hash != bkp_hash:
        destino.unlink(missing_ok=True)
        raise RuntimeError("Backup FALHOU — tamanho ou hash divergem. Migracao abortada.")

    log.info("Backup OK | tamanho=%d bytes | sha256=%s...", bkp_size, bkp_hash[:16])
    return destino

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDAÇÃO CPF / CNS
# ══════════════════════════════════════════════════════════════════════════════

def _so_digitos(v: str | None) -> str:
    return re.sub(r"\D", "", v or "")

def validar_cpf(cpf: str) -> bool:
    cpf = _so_digitos(cpf)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    for i in range(2):
        n = 10 + i
        soma = sum(int(cpf[j]) * (n - j) for j in range(9 + i))
        d = (soma * 10) % 11
        if d >= 10:
            d = 0
        if d != int(cpf[9 + i]):
            return False
    return True

def validar_cns(cns: str) -> bool:
    cns = _so_digitos(cns)
    if len(cns) != 15 or not cns.isdigit() or cns[0] not in "12789":
        return False
    soma = sum(int(cns[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

# ══════════════════════════════════════════════════════════════════════════════
#  NORMALIZAÇÃO DE CAMPOS
# ══════════════════════════════════════════════════════════════════════════════

def _norm_str(v: str | None, maxlen: int | None = None) -> str | None:
    if not v:
        return None
    v = v.strip().upper()
    if maxlen:
        v = v[:maxlen]
    return v or None

def _norm_sexo(v: str | None) -> str | None:
    v = (v or "").strip().upper()
    if v in ("M", "MASCULINO", "MASC"):
        return "M"
    if v in ("F", "FEMININO", "FEM"):
        return "F"
    return None

def _norm_raca(v: str | None) -> str:
    v = (v or "").strip().upper()
    if v in ("01", "02", "03", "04", "05"):
        return v
    return _RACA_MAP.get(v, "03")

def _norm_telefone(v: str | None) -> tuple[str | None, str | None]:
    digits = _so_digitos(v)
    if len(digits) >= 10:
        return digits[:2], digits[2:11]  # DDD + até 9 dígitos
    return None, None

_DATE_FMTS = [
    ("%d/%m/%Y", 8),
    ("%Y-%m-%d", 8),
    ("%d-%m-%Y", 8),
    ("%Y/%m/%d", 8),
    ("%d%m%Y",   8),
]

def _parse_dtnasc(v: str | None) -> tuple[str, bool]:
    """Retorna (dtnasc_YYYYMMDD, data_corrigida)."""
    if not v or not v.strip():
        return _DEFAULT_DTNASC, True
    v = v.strip()
    # Já está no formato YYYYMMDD
    if re.fullmatch(r"\d{8}", v):
        try:
            d = datetime.strptime(v, "%Y%m%d")
            if 1900 <= d.year <= datetime.now().year:
                return v, False
        except ValueError:
            pass
    for fmt, _ in _DATE_FMTS:
        try:
            d = datetime.strptime(v, fmt)
            if 1900 <= d.year <= datetime.now().year:
                return d.strftime("%Y%m%d"), False
        except ValueError:
            continue
    return _DEFAULT_DTNASC, True

def _parse_registro(v: str | None) -> int | None:
    if not v or not v.strip():
        return None
    try:
        n = int(v.strip())
        return n if -32768 <= n <= 32767 else None
    except ValueError:
        return None

def _parse_datetime_atd(data: str | None, hora: str | None) -> datetime | None:
    if not data:
        return None
    try:
        hora = (hora or "00:00").strip()
        return datetime.strptime(f"{data.strip()} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(data.strip(), "%Y-%m-%d")
        except ValueError:
            return None

# ══════════════════════════════════════════════════════════════════════════════
#  CONEXÕES
# ══════════════════════════════════════════════════════════════════════════════

def conectar_sqlite() -> sqlite3.Connection:
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"SQLite nao encontrado: {SQLITE_PATH}")
    uri = f"file:{SQLITE_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    log.info("SQLite (somente leitura): %s", SQLITE_PATH)
    return conn

def conectar_postgres() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        dbname=POSTGRES_DB, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    conn.autocommit = False
    log.info("PostgreSQL: %s:%d/%s (user=%s)", POSTGRES_HOST, POSTGRES_PORT,
             POSTGRES_DB, POSTGRES_USER)
    return conn

# ══════════════════════════════════════════════════════════════════════════════
#  UNION-FIND — deduplicação em memória
# ══════════════════════════════════════════════════════════════════════════════

class UnionFind:
    def __init__(self):
        self._parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        if x not in self._parent:
            self._parent[x] = x

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[ry] = rx

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for x in self._parent:
            root = self.find(x)
            result.setdefault(root, []).append(x)
        return result

# ══════════════════════════════════════════════════════════════════════════════
#  DADOS LEGADOS — carregamento e processamento
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PacienteLegado:
    sqlite_key: str        # chave primária do SQLite (cpf bruto)
    cpf:        str | None # CPF normalizado (só dígitos), None se inválido
    cns:        str | None # CNS normalizado, None se inválido
    nome:       str | None
    nome_social:str | None
    dtnasc:     str
    dtnasc_corrigida: bool
    sexo:       str | None
    raca:       str
    maepcn:     str | None
    responsavel:str | None
    civil:      str | None
    ocupacao:   str | None
    naturalidade:str | None
    ddtel:      str | None
    tel:        str | None
    logpcn:     str
    numpcn:     str
    bairro:     str
    cidade:     str | None
    estado:     str | None
    n_atendimentos: int = 0   # preenchido após JOIN com atendimentos

    def score(self) -> int:
        """Pontuação para seleção do registro campeão no grupo."""
        campos = [self.nome, self.sexo, self.maepcn, self.responsavel,
                  self.civil, self.ocupacao, self.naturalidade,
                  self.ddtel, self.tel, self.cidade, self.estado]
        s = sum(1 for c in campos if c)
        if self.cpf:  s += 10
        if self.cns:  s += 10
        if not self.dtnasc_corrigida: s += 5
        if self.logpcn != _DEFAULT_LOGPCN: s += 2
        if self.bairro != _DEFAULT_BAIRRO: s += 2
        s += min(self.n_atendimentos, 50)
        return s


def _carregar_pacientes_sqlite(
    conn: sqlite3.Connection,
    ctrs: Counters,
) -> tuple[list[PacienteLegado], dict[str, int]]:
    """
    Carrega pacientes do SQLite, normaliza e valida.
    Retorna (lista de PacienteLegados válidos, mapa {sqlite_key: n_atendimentos}).
    """
    cur = conn.cursor()

    # Conta atendimentos por CPF/SUS no legado para pontuação
    cur.execute("""
        SELECT cpf, sus, COUNT(*) as n
        FROM atendimentos
        GROUP BY cpf, sus
    """)
    atd_por_cpf: dict[str, int] = {}
    atd_por_sus: dict[str, int] = {}
    for row in cur.fetchall():
        cpf_d = _so_digitos(row["cpf"])
        sus_d = _so_digitos(row["sus"])
        n = row["n"]
        if cpf_d: atd_por_cpf[cpf_d] = atd_por_cpf.get(cpf_d, 0) + n
        if sus_d: atd_por_sus[sus_d]  = atd_por_sus.get(sus_d,  0) + n

    cur.execute("SELECT COUNT(*) FROM pacientes")
    ctrs.pac_total_sqlite = cur.fetchone()[0]

    cur.execute("""
        SELECT cpf, sus, nome, nomeSocial, naturalidade, dn, idade,
               sexo, civil, raca, ocupacao, mae, responsavel,
               tel, endereco, numero, bairro, cidade, estado
        FROM pacientes
    """)

    pacientes: list[PacienteLegado] = []

    for row in cur.fetchall():
        sqlite_key = str(row["cpf"] or "")

        cpf_raw = _so_digitos(row["cpf"])
        cns_raw = _so_digitos(row["sus"])

        cpf = cpf_raw if validar_cpf(cpf_raw) else None
        cns = cns_raw if validar_cns(cns_raw) else None

        # Regra: deve ter ao menos um identificador válido
        if not cpf and not cns:
            ctrs.pac_ignorados_semid += 1
            log.debug("IGNORADO (sem CPF/CNS válido): nome=%s cpf_raw=%s sus_raw=%s",
                      row["nome"], row["cpf"], row["sus"])
            continue

        dtnasc, corrigida = _parse_dtnasc(row["dn"])
        if corrigida:
            ctrs.pac_datas_corrigidas += 1

        ddtel, tel = _norm_telefone(row["tel"])

        n_atd = (atd_por_cpf.get(cpf_raw, 0) if cpf_raw else 0) + \
                (atd_por_sus.get(cns_raw,  0) if cns_raw else 0)

        p = PacienteLegado(
            sqlite_key   = sqlite_key,
            cpf          = cpf,
            cns          = cns,
            nome         = _norm_str(row["nome"], 100),
            nome_social  = _norm_str(row["nomeSocial"], 100),
            dtnasc       = dtnasc,
            dtnasc_corrigida = corrigida,
            sexo         = _norm_sexo(row["sexo"]),
            raca         = _norm_raca(row["raca"]),
            maepcn       = _norm_str(row["mae"], 100),
            responsavel  = _norm_str(row["responsavel"], 100),
            civil        = _norm_str(row["civil"], 50),
            ocupacao     = _norm_str(row["ocupacao"], 100),
            naturalidade = _norm_str(row["naturalidade"], 100),
            ddtel        = ddtel,
            tel          = tel,
            logpcn       = _norm_str(row["endereco"], 100) or _DEFAULT_LOGPCN,
            numpcn       = _norm_str(row["numero"], 100)   or _DEFAULT_NUMPCN,
            bairro       = _norm_str(row["bairro"], 100)   or _DEFAULT_BAIRRO,
            cidade       = _norm_str(row["cidade"], 100),
            estado       = _norm_str(row["estado"], 2),
            n_atendimentos = n_atd,
        )
        pacientes.append(p)
        ctrs.pac_validos += 1

    ctrs.pac_ignorados_invalidos = ctrs.pac_total_sqlite - ctrs.pac_validos - ctrs.pac_ignorados_semid
    return pacientes, atd_por_cpf


def _deduplicar_pacientes(
    pacientes: list[PacienteLegado],
    ctrs: Counters,
) -> list[PacienteLegado]:
    """
    Agrupa pacientes que compartilham CPF ou CNS após normalização.
    Retorna apenas os campeões (um por grupo), com n_atendimentos consolidado.
    """
    uf = UnionFind()

    # Índices por CPF e CNS para unir grupos
    cpf_to_key: dict[str, str] = {}
    cns_to_key: dict[str, str] = {}

    for p in pacientes:
        key = p.sqlite_key or (p.cpf or p.cns or id(p))
        key = str(key)
        uf.add(key)
        if p.cpf:
            if p.cpf in cpf_to_key:
                uf.union(cpf_to_key[p.cpf], key)
            else:
                cpf_to_key[p.cpf] = key
        if p.cns:
            if p.cns in cns_to_key:
                uf.union(cns_to_key[p.cns], key)
            else:
                cns_to_key[p.cns] = key

    # Mapeia key → PacienteLegado
    key_map: dict[str, PacienteLegado] = {str(p.sqlite_key or id(p)): p for p in pacientes}

    # Para cada grupo, escolhe o campeão e soma atendimentos
    grupos = uf.groups()
    campeoes: list[PacienteLegado] = []

    for root, membros in grupos.items():
        grupo_pacs = [key_map[m] for m in membros if m in key_map]
        if not grupo_pacs:
            continue

        # Soma todos os atendimentos do grupo no campeão
        total_atd = sum(p.n_atendimentos for p in grupo_pacs)

        # Escolhe campeão: maior pontuação
        campiao = max(grupo_pacs, key=lambda p: p.score())
        campiao.n_atendimentos = total_atd

        fundidos = len(grupo_pacs) - 1
        if fundidos > 0:
            ctrs.pac_duplicatas_fundidas += fundidos
            nomes = [p.nome or "?" for p in grupo_pacs]
            log.debug("FUSAO de %d registros → campeao=%s | grupo=%s",
                      len(grupo_pacs), campiao.nome, " / ".join(nomes))

        campeoes.append(campiao)

    return campeoes

# ══════════════════════════════════════════════════════════════════════════════
#  MIGRAÇÃO — PACIENTES
# ══════════════════════════════════════════════════════════════════════════════

def _carregar_mapa_pg(pg: psycopg2.extensions.connection) -> tuple[dict, dict]:
    """Retorna {cpf_digits: pg_id} e {cns_digits: pg_id} dos pacientes já no PG."""
    cur = pg.cursor()
    cur.execute("SELECT id, num_cpf, cns FROM pacientes")
    cpf_map: dict[str, int] = {}
    cns_map: dict[str, int] = {}
    for row in cur.fetchall():
        pid, cpf, cns = row
        if cpf: cpf_map[_so_digitos(cpf)] = pid
        if cns: cns_map[_so_digitos(cns)]  = pid
    cur.close()
    return cpf_map, cns_map


def migrar_pacientes(
    pg: psycopg2.extensions.connection,
    campeoes: list[PacienteLegado],
    ctrs: Counters,
    dry_run: bool,
) -> dict[str, int]:
    """
    Insere pacientes no PostgreSQL.
    Retorna mapa {cpf_ou_cns_normalizado: pg_id} para resolução de atendimentos.
    """
    cpf_map, cns_map = _carregar_mapa_pg(pg)
    log.info("Pacientes ja existentes no PG: %d por CPF, %d por CNS",
             len(cpf_map), len(cns_map))

    batch: list[tuple] = []
    # cpf/cns → pg_id (inclui existentes + novos)
    resolucao: dict[str, int] = {**{f"cpf:{k}": v for k, v in cpf_map.items()},
                                  **{f"cns:{k}": v for k, v in cns_map.items()}}

    def flush():
        nonlocal batch
        if not batch or dry_run:
            if dry_run and batch:
                log.info("[DRY-RUN] Simularia inserir %d pacientes", len(batch))
                ctrs.pac_inseridos += len(batch)
            batch = []
            return
        cur = pg.cursor()
        execute_values(cur, """
            INSERT INTO pacientes
                (cns, num_cpf, nome, nome_social, dtnasc, sexo, raca,
                 maepcn, responsavel, civil, ocupacao, naturalidade,
                 ddtel_pcnte, tel_pcnte,
                 logpcn, numpcn, bairro_pcnte,
                 cidade, estado,
                 ibge, ceppcn, co_lograd, nacionalidade)
            VALUES %s
            RETURNING id, num_cpf, cns
        """, batch, fetch=True)
        rows = cur.fetchall()
        pg.commit()
        for pid, cpf, cns in rows:
            if cpf: resolucao[f"cpf:{_so_digitos(cpf)}"] = pid
            if cns: resolucao[f"cns:{_so_digitos(cns)}"]  = pid
        ctrs.pac_inseridos += len(rows)
        cur.close()
        batch = []

    for p in campeoes:
        # Já existe?
        pg_id = None
        if p.cpf and (pg_id := cpf_map.get(p.cpf)):
            ctrs.pac_ja_existiam += 1
            resolucao[f"cpf:{p.cpf}"] = pg_id
            if p.cns: resolucao[f"cns:{p.cns}"] = pg_id
            continue
        if p.cns and (pg_id := cns_map.get(p.cns)):
            ctrs.pac_ja_existiam += 1
            resolucao[f"cns:{p.cns}"] = pg_id
            if p.cpf: resolucao[f"cpf:{p.cpf}"] = pg_id
            continue

        batch.append((
            p.cns, p.cpf, p.nome, p.nome_social, p.dtnasc,
            p.sexo, p.raca, p.maepcn, p.responsavel, p.civil,
            p.ocupacao, p.naturalidade, p.ddtel, p.tel,
            p.logpcn, p.numpcn, p.bairro,
            p.cidade, p.estado,
            _DEFAULT_IBGE, _DEFAULT_CEP, _DEFAULT_LOGRAD, _DEFAULT_NACIONAL,
        ))

        if len(batch) >= BATCH_SIZE:
            flush()

    flush()
    return resolucao

# ══════════════════════════════════════════════════════════════════════════════
#  MIGRAÇÃO — ATENDIMENTOS
# ══════════════════════════════════════════════════════════════════════════════

def _carregar_existentes_atd(pg: psycopg2.extensions.connection) -> set[tuple]:
    cur = pg.cursor()
    cur.execute(
        "SELECT paciente_id, date_trunc('minute', data_atendimento) "
        "FROM recepcao_atendimentos"
    )
    existentes = {(row[0], row[1]) for row in cur.fetchall()}
    cur.close()
    log.info("Atendimentos ja existentes no PG: %d", len(existentes))
    return existentes


def migrar_atendimentos(
    sqlite_conn: sqlite3.Connection,
    pg: psycopg2.extensions.connection,
    resolucao: dict[str, int],
    ctrs: Counters,
    dry_run: bool,
) -> None:
    existentes = _carregar_existentes_atd(pg)

    cur_sqlite = sqlite_conn.cursor()
    cur_sqlite.execute("SELECT COUNT(*) FROM atendimentos")
    ctrs.atd_total_sqlite = cur_sqlite.fetchone()[0]
    log.info("Atendimentos no SQLite: %d", ctrs.atd_total_sqlite)

    cur_sqlite.execute(
        "SELECT cpf, sus, data_atendimento, hora_atendimento, registro, procedencia "
        "FROM atendimentos ORDER BY id"
    )

    batch: list[tuple] = []
    now = datetime.now(timezone.utc)

    def flush():
        if not batch or dry_run:
            if dry_run and batch:
                log.info("[DRY-RUN] Simularia inserir %d atendimentos", len(batch))
                ctrs.atd_migrados += len(batch)
            batch.clear()
            return
        cur = pg.cursor()
        execute_values(cur, """
            INSERT INTO recepcao_atendimentos
                (paciente_id, data_atendimento, registro, procedencia,
                 created_at, updated_at)
            VALUES %s
        """, batch)
        pg.commit()
        ctrs.atd_migrados += cur.rowcount
        cur.close()
        batch.clear()

    for row in cur_sqlite:
        cpf_d = _so_digitos(row["cpf"])
        cns_d = _so_digitos(row["sus"])

        # Resolver pg_id via cpf ou cns
        pg_id = resolucao.get(f"cpf:{cpf_d}") or resolucao.get(f"cns:{cns_d}")
        if not pg_id:
            ctrs.atd_sem_paciente += 1
            log.debug("ATD sem paciente no PG: cpf=%s cns=%s", row["cpf"], row["sus"])
            continue

        dt = _parse_datetime_atd(row["data_atendimento"], row["hora_atendimento"])
        if not dt:
            ctrs.atd_data_invalida += 1
            continue

        # Deduplicação em memória
        chave = (pg_id, dt.replace(second=0, microsecond=0))
        if chave in existentes:
            ctrs.atd_duplicatas += 1
            continue
        existentes.add(chave)

        registro  = _parse_registro(row["registro"])
        procedencia = (_norm_str(row["procedencia"]) or None)

        batch.append((pg_id, dt, registro, procedencia, now, now))

        if len(batch) >= BATCH_SIZE:
            flush()
            log.info("  Atendimentos: migrados=%d dup=%d sem_pac=%d",
                     ctrs.atd_migrados, ctrs.atd_duplicatas, ctrs.atd_sem_paciente)

    flush()

# ══════════════════════════════════════════════════════════════════════════════
#  ORQUESTRADOR
# ══════════════════════════════════════════════════════════════════════════════

def _separador(titulo: str = "") -> None:
    log.info("=" * 58)
    if titulo:
        log.info("  %s", titulo)
        log.info("=" * 58)


def migrar(dry_run: bool, skip_backup: bool) -> None:
    ctrs = Counters()

    _separador("MIGRAÇÃO OFICIAL HMPCF — SQLite → PostgreSQL")
    log.info("  Origem  : %s", SQLITE_PATH)
    log.info("  Destino : %s:%d/%s", POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB)
    log.info("  Modo    : %s", "DRY-RUN (sem escrita)" if dry_run else "PRODUCAO")
    log.info("  Log     : %s", LOG_FILE)
    _separador()

    # ── 1. Backup ─────────────────────────────────────────────────────────────
    log.info("[1/5] Backup do SQLite legado...")
    fazer_backup(skip=skip_backup)

    # ── 2. Conexões ───────────────────────────────────────────────────────────
    log.info("[2/5] Conectando bancos...")
    sqlite_conn = conectar_sqlite()
    pg_conn     = conectar_postgres()

    try:
        # ── 3. Pacientes: carregar + processar + deduplicar ───────────────────
        log.info("[3/5] Carregando e processando pacientes do SQLite...")
        pacientes, _ = _carregar_pacientes_sqlite(sqlite_conn, ctrs)
        log.info("  Válidos carregados: %d | Sem ID: %d",
                 ctrs.pac_validos, ctrs.pac_ignorados_semid)

        log.info("  Deduplicando por CPF/CNS (union-find)...")
        campeoes = _deduplicar_pacientes(pacientes, ctrs)
        log.info("  Grupos únicos: %d | Duplicatas fundidas: %d",
                 len(campeoes), ctrs.pac_duplicatas_fundidas)

        # ── 4. Migrar pacientes ───────────────────────────────────────────────
        log.info("[4/5] Migrando pacientes para PostgreSQL...")
        resolucao = migrar_pacientes(pg_conn, campeoes, ctrs, dry_run)
        log.info("  Inseridos: %d | Já existiam: %d | Datas corrigidas: %d",
                 ctrs.pac_inseridos, ctrs.pac_ja_existiam, ctrs.pac_datas_corrigidas)

        # ── 5. Migrar atendimentos ────────────────────────────────────────────
        log.info("[5/5] Migrando atendimentos para PostgreSQL...")
        migrar_atendimentos(sqlite_conn, pg_conn, resolucao, ctrs, dry_run)
        log.info("  Migrados: %d | Duplicatas: %d | Sem paciente: %d | Data inválida: %d",
                 ctrs.atd_migrados, ctrs.atd_duplicatas, ctrs.atd_sem_paciente,
                 ctrs.atd_data_invalida)

    except Exception:
        log.exception("ERRO CRITICO — realizando rollback.")
        try:
            pg_conn.rollback()
        except Exception:
            pass
        raise

    finally:
        sqlite_conn.close()
        pg_conn.close()

    # ── Relatório final ───────────────────────────────────────────────────────
    _separador("RELATÓRIO FINAL")
    log.info("")
    log.info("  PACIENTES")
    log.info("  %-35s %8d", "Total no SQLite:", ctrs.pac_total_sqlite)
    log.info("  %-35s %8d", "Válidos processados:", ctrs.pac_validos)
    log.info("  %-35s %8d", "Sem CPF/CNS válido (ignorados):", ctrs.pac_ignorados_semid)
    log.info("  %-35s %8d", "Duplicatas fundidas (conservadas):", ctrs.pac_duplicatas_fundidas)
    log.info("  %-35s %8d%s", "Inseridos no PostgreSQL:", ctrs.pac_inseridos,
             "  (simulado)" if dry_run else "")
    log.info("  %-35s %8d", "Já existiam no PostgreSQL:", ctrs.pac_ja_existiam)
    log.info("  %-35s %8d", "Datas de nascimento corrigidas:", ctrs.pac_datas_corrigidas)
    log.info("")
    log.info("  ATENDIMENTOS")
    log.info("  %-35s %8d", "Total no SQLite:", ctrs.atd_total_sqlite)
    log.info("  %-35s %8d%s", "Migrados:", ctrs.atd_migrados,
             "  (simulado)" if dry_run else "")
    log.info("  %-35s %8d", "Duplicatas removidas:", ctrs.atd_duplicatas)
    log.info("  %-35s %8d", "Sem paciente no PG:", ctrs.atd_sem_paciente)
    log.info("  %-35s %8d", "Data/hora inválida:", ctrs.atd_data_invalida)
    log.info("")
    log.info("  STATUS: %s", "CONCLUÍDA COM SUCESSO" if not dry_run else "DRY-RUN OK — nada foi gravado")
    _separador()

# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migração OFICIAL SQLite → PostgreSQL — HMPCF"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simula sem gravar nada no PostgreSQL")
    parser.add_argument("--skip-backup", action="store_true",
                        help="Pula backup automático (use apenas em ambiente de teste)")
    args = parser.parse_args()

    if args.dry_run:
        log.info(">>> MODO DRY-RUN: nenhum dado sera gravado no PostgreSQL <<<")

    migrar(dry_run=args.dry_run, skip_backup=args.skip_backup)


if __name__ == "__main__":
    main()
