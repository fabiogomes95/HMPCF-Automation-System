"""
CONSULTA_RECEPCAO.PY — Consulta e estatísticas da recepção (hospital.db)
=======================================================================
CARREGA TUDO NA RAM na inicialização (igual carregar_base do Firebird).
Consultas são instantâneas e não bloqueiam o Eel.
"""

import os
import sqlite3
from logging_setup import logger
from config import DB_SQLITE

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ATENDIMENTOS: list[dict] = []
_PACIENTES_MAP: dict[str, dict] = {}
_CARREGADO = False
_STATUS_MSG = "Aguardando carga..."


def _db_path() -> str:
    path = DB_SQLITE
    if not os.path.isabs(path):
        path = os.path.join(SRC_DIR, path)
    return path


def carregar() -> str:
    """Carrega hospital.db inteiro na RAM. Chamado na inicialização do app_painel."""
    global _ATENDIMENTOS, _PACIENTES_MAP, _CARREGADO, _STATUS_MSG
    path = _db_path()

    if not os.path.exists(path):
        _CARREGADO = False
        _STATUS_MSG = f"hospital.db nao encontrado em: {path}"
        logger.warning(_STATUS_MSG)
        return _STATUS_MSG

    try:
        conn = sqlite3.connect(path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM pacientes")
        pacientes = cursor.fetchall()
        cols_p = [d[0] for d in cursor.description]
        _PACIENTES_MAP = {}
        for row in pacientes:
            d = dict(zip(cols_p, row))
            if d.get("cpf"):
                _PACIENTES_MAP[d["cpf"]] = d
            if d.get("sus"):
                _PACIENTES_MAP[d["sus"]] = d

        cursor.execute("""
            SELECT
                a.id, a.data_atendimento, a.hora_atendimento,
                a.registro, a.procedencia, a.cpf, a.sus
            FROM atendimentos a
            ORDER BY a.data_atendimento DESC, a.hora_atendimento DESC
        """)
        rows = cursor.fetchall()
        cols_a = [d[0] for d in cursor.description]

        _ATENDIMENTOS = []
        for row in rows:
            a = dict(zip(cols_a, row))
            pac = _PACIENTES_MAP.get(a.get("cpf")) or _PACIENTES_MAP.get(a.get("sus"))
            if pac:
                a["nome"] = pac.get("nome", "")
                a["dn"] = pac.get("dn", "")
                a["endereco"] = pac.get("endereco", "")
                a["bairro"] = pac.get("bairro", "")
                a["cidade"] = pac.get("cidade", "")
                a["tel"] = pac.get("tel", "")
            else:
                a["nome"] = ""
                a["dn"] = ""
                a["endereco"] = ""
                a["bairro"] = ""
                a["cidade"] = ""
                a["tel"] = ""
            _ATENDIMENTOS.append(a)

        conn.close()
        _CARREGADO = True
        _STATUS_MSG = f"OK: {len(pacientes)} pacientes, {len(_ATENDIMENTOS)} atendimentos na RAM"
        logger.info(_STATUS_MSG)
        return _STATUS_MSG

    except Exception as e:
        _CARREGADO = False
        _STATUS_MSG = f"Erro ao carregar hospital.db: {e}"
        logger.error(_STATUS_MSG)
        return _STATUS_MSG


def status() -> str:
    """Retorna status atual do cache sem recarregar."""
    return _STATUS_MSG


def consultar_atendimentos(data_inicio: str, data_fim: str) -> list[dict]:
    if not _CARREGADO:
        return []
    resultado = []
    for a in _ATENDIMENTOS:
        if data_inicio <= (a.get("data_atendimento") or "") <= data_fim:
            resultado.append(a)
    logger.info(f"Consulta RAM: {len(resultado)} linhas")
    return resultado


def resumo_atendimentos(data_inicio: str, data_fim: str) -> dict:
    if not _CARREGADO:
        return {"total": 0, "por_procedencia": {}, "media_dia": 0}

    total = 0
    por_procedencia: dict[str, int] = {}
    dias: set[str] = set()

    for a in _ATENDIMENTOS:
        data = a.get("data_atendimento") or ""
        if not (data_inicio <= data <= data_fim):
            continue
        total += 1
        proc = a.get("procedencia") or "NORMAL"
        por_procedencia[proc] = por_procedencia.get(proc, 0) + 1
        dias.add(data)

    return {
        "total": total,
        "por_procedencia": por_procedencia,
        "media_dia": round(total / max(len(dias), 1), 1),
    }


def atendimentos_por_dia(data_inicio: str, data_fim: str) -> list[dict]:
    if not _CARREGADO:
        return []

    dia_map: dict[str, int] = {}
    for a in _ATENDIMENTOS:
        data = a.get("data_atendimento") or ""
        if not (data_inicio <= data <= data_fim):
            continue
        dia_map[data] = dia_map.get(data, 0) + 1

    return sorted(
        [{"data": d, "qtd": q} for d, q in dia_map.items()],
        key=lambda x: x["data"],
    )
