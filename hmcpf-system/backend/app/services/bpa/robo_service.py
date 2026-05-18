from __future__ import annotations

import json
import os
import subprocess
import sys
from logging import getLogger

from app.core.config import settings
from app.database import firebird as fb
from app.repositories import producao_repository as producao_repo
from app.services.bpa.producao_service import _automacao_path, _parse_header

logger = getLogger(__name__)

_processos_rpa: dict[int, dict] = {}


def _robo_pid_valido(pid: int) -> bool:
    try:
        proc = subprocess.Popen(["tasklist", "/FI", f"PID eq {pid}", "/NH"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        out, _ = proc.communicate(timeout=5)
        return str(pid) in out.decode("utf-8", errors="ignore")
    except Exception:
        return False


def robo_preparar(nome_arquivo: str) -> dict:
    caminho = _automacao_path(nome_arquivo)
    if not os.path.exists(caminho):
        return {"lotes": [], "erro": "Arquivo nao encontrado."}

    doc_validos: set[str] = set()
    try:
        doc_validos = fb.carregar_documentos_firebird()
    except Exception as e:
        logger.warning(f"Erro ao carregar Firebird: {e}")

    linhas = producao_repo.ler_linhas(caminho)

    lotes = []
    lote_atual: dict | None = None

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if linha.startswith("PROFISSIONAL:"):
            if lote_atual:
                lotes.append(lote_atual)
            medico, data = _parse_header(linha)
            lote_atual = {"medico": medico, "data": data, "pacientes": [], "validados": []}
        elif lote_atual:
            if linha in doc_validos:
                lote_atual["validados"].append(linha)
                lote_atual["pacientes"].append(linha)
            else:
                lote_atual["pacientes"].append(linha)

    if lote_atual:
        lotes.append(lote_atual)

    return {"lotes": lotes, "erro": ""}


def robo_executar(medico: str, data: str, procedimento: str, pacientes: list[str]) -> dict:
    automacao_dir = os.path.join(os.path.dirname(settings.PROJECT_ROOT), "automacao")
    executor_path = os.path.join(automacao_dir, "executor_rpa.py")

    if not os.path.exists(executor_path):
        return {"status": "erro", "mensagem": f"executor_rpa.py nao encontrado: {executor_path}"}

    pacientes_json = json.dumps(pacientes)
    script = (
        f"import sys; sys.path.insert(0, {json.dumps(automacao_dir)}); "
        f"from executor_rpa import executar_pyautogui; "
        f"executar_pyautogui({json.dumps(medico)}, {json.dumps(data)}, "
        f"{json.dumps(procedimento)}, {pacientes_json})"
    )

    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            cwd=automacao_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        pid = proc.pid
        _processos_rpa[pid] = {
            "medico": medico,
            "data": data,
            "pacientes": len(pacientes),
        }
        logger.info(f"RPA iniciado PID={pid} | {medico} | {len(pacientes)} pacientes")
        return {"status": "ok", "pid": pid, "mensagem": "Robô RPA iniciado"}
    except Exception as e:
        logger.error(f"Erro ao executar RPA: {e}")
        return {"status": "erro", "mensagem": str(e)}


def robo_status(pid: int) -> dict:
    info = _processos_rpa.get(pid)
    if not info:
        return {"status": "desconhecido", "mensagem": "PID nao encontrado"}
    rodando = _robo_pid_valido(pid)
    if not rodando:
        _processos_rpa.pop(pid, None)
    return {"status": "executando" if rodando else "concluido", **info}
