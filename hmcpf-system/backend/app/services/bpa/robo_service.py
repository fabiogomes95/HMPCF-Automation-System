from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from logging import getLogger

from app.core.config import settings
from app.database import firebird as fb
from app.repositories import cadcns_repository as cadcns_repo
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


def buscar_paciente_no_banco(documento: str) -> dict | None:
    try:
        con = fb.get_firebird_conn()
    except Exception as e:
        logger.error("buscar_paciente_no_banco: erro ao conectar: %s", e)
        return None
    try:
        return cadcns_repo.buscar_por_documento(con, documento)
    except Exception as e:
        logger.error("buscar_paciente_no_banco: erro ao buscar '%s': %s", documento, e)
        return None
    finally:
        try:
            con.close()
        except Exception:
            pass


def preparar_lotes(arq_leitura: str, callback: callable | None = None) -> tuple[list, str]:
    caminho = _automacao_path(arq_leitura)
    if not os.path.exists(caminho):
        return [], "Ficheiro não encontrado."

    with open(caminho, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    lotes: list[dict] = []
    lote_atual: dict | None = None
    ignorados = 0

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        if "PROFISSIONAL:" in linha:
            if lote_atual:
                lotes.append(lote_atual)
            medico, data = _parse_header(linha)
            lote_atual = {
                "medico": medico,
                "data": data,
                "pacientes": [],
                "ignorados": [],
            }
        elif lote_atual:
            paciente = buscar_paciente_no_banco(linha)
            if paciente:
                lote_atual["pacientes"].append(paciente)
                if callback:
                    callback(f"✅ {paciente['nome']} ({linha})")
            else:
                ignorados += 1
                lote_atual["ignorados"].append(linha)
                if callback:
                    callback(f"⚠️  {linha} — sem cadastro ou campos obrigatórios vazios")

    if lote_atual:
        lotes.append(lote_atual)

    if callback:
        callback(f"\n📊 Lotes: {len(lotes)} | Ignorados: {ignorados}")

    return lotes, ""


def executar_pyautogui(medico: str, data_atend: str, procedimento: str,
                        pacientes: list[dict], callback: callable | None = None) -> int:
    try:
        import keyboard
        import pyautogui
        pyautogui.FAILSAFE = True
    except ImportError:
        logger.error("executar_pyautogui: pyautogui/keyboard nao instalados")
        return -1

    data_limpa = "".join(c for c in data_atend if c.isdigit())
    total = len(pacientes)
    processados = 0

    for i, p in enumerate(pacientes, 1):
        try:
            if keyboard.is_pressed("esc"):
                if callback:
                    callback("🛑 INTERROMPIDO PELO USUÁRIO (ESC)")
                break
        except Exception:
            pass

        doc = p.get("documento", p.get("documento_paciente", ""))
        if not doc:
            doc = p.get("cns", p.get("cpf", ""))
        if not doc:
            continue

        if callback:
            callback(f"🚀 {medico} | {i}/{total} | {p.get('nome', '')} | Doc: {doc}")

        try:
            pyautogui.write(doc)
            pyautogui.press("f7")
            time.sleep(1.0)

            pyautogui.write(data_limpa)
            pyautogui.press("tab")

            pyautogui.write(procedimento)
            pyautogui.press("1")
            time.sleep(0.5)

            pyautogui.press(["tab", "tab", "tab"])
            pyautogui.write("2")
            time.sleep(0.3)

            pyautogui.press(["tab", "tab"])
            pyautogui.press("enter")
            time.sleep(1.0)

            processados += 1

        except Exception as e:
            if callback:
                callback(f"❌ Erro em {doc}: {e}")
            continue

    return processados
