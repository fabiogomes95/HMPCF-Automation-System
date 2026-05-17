from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from logging import getLogger
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = getLogger(__name__)

_AUTOMACAO_DIR: Path = settings.PROJECT_ROOT.parent / "automacao"


def _automacao_path(arquivo: str = "") -> str:
    return str(_AUTOMACAO_DIR / (arquivo or ""))


def _get_legacy_conn() -> sqlite3.Connection:
    db_path = settings.PROJECT_ROOT.parent / "hospital.db"
    if not db_path.exists():
        raise FileNotFoundError(f"hospital.db nao encontrado: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


_ISQL_PATH = r"C:\Program Files (x86)\Firebird\Firebird_1_5\bin\isql.exe"
_FB_PATH = r"C:\BPA\BPAMAG.GDB"


def _carregar_documentos_firebird() -> set[str]:
    """Carrega CPF e CNS do CADCNS (Firebird) como conjunto de documentos válidos."""
    documentos: set[str] = set()
    if not os.path.exists(_ISQL_PATH) or not os.path.exists(_FB_PATH):
        return documentos

    sql_file = os.path.join(tempfile.gettempdir(), "fb_query_cpf.txt")
    try:
        with open(sql_file, "w", encoding="ascii") as f:
            f.write("SELECT NUM_CPF, CNS FROM CADCNS;\n")
        resultado = subprocess.run(
            [_ISQL_PATH, "-q", _FB_PATH, "-u", "SYSDBA", "-p", "masterkey", "-i", sql_file],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        for linha in resultado.stdout.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("=") or linha.startswith("NUM_CPF") or linha.startswith("CNS"):
                continue
            partes = linha.split()
            for p in partes:
                p = p.strip()
                if p and len(p) in (11, 15) and p.isdigit():
                    documentos.add(p)
        logger.info(f"Firebird: {len(documentos)} documentos carregados do CADCNS")
    except Exception as e:
        logger.warning(f"Firebird nao disponivel: {e}")
    finally:
        try:
            os.remove(sql_file)
        except Exception:
            pass
    return documentos


# ── VALIDAÇÃO ────────────────────────────────────────────────


def _apenas_numeros(valor: str | None) -> str:
    return re.sub(r"\D", "", str(valor)) if valor else ""


def _valida_cpf(cpf: str | None) -> bool:
    c = _apenas_numeros(cpf)
    if not c or len(c) != 11 or len(set(c)) == 1:
        return False
    s1 = sum(int(c[i]) * (10 - i) for i in range(9))
    d1 = (s1 * 10 % 11) % 10
    s2 = sum(int(c[i]) * (11 - i) for i in range(10))
    d2 = (s2 * 10 % 11) % 10
    return str(d1) == c[9] and str(d2) == c[10]


def _valida_cns(cns: str | None) -> bool:
    c = _apenas_numeros(cns)
    if len(c) != 15 or c[0] not in "12789":
        return False
    if c[0] in "789":
        return sum(int(c[i]) * (15 - i) for i in range(15)) % 11 == 0
    pis = c[:11]
    soma = sum(int(pis[i]) * (15 - i) for i in range(11))
    resto = soma % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    if dv == 10:
        soma += 2
        resto = soma % 11
        dv = 11 - resto
        resultado = pis + "001" + str(dv)
    else:
        resultado = pis + "000" + str(dv)
    return c == resultado


# ── 1. PRODUÇÕES (arquivos .txt) ────────────────────────────


def listar_producoes() -> list[str]:
    pattern = os.path.join(_automacao_path(), "*.txt")
    arquivos = glob.glob(pattern)
    nomes = [os.path.basename(a) for a in arquivos]
    nomes.sort(reverse=True)
    # Filtra arquivos de sistema
    nomes = [n for n in nomes if not n.startswith("cpf_sus")]
    return nomes


def ler_producao(nome_arquivo: str) -> str:
    caminho = _automacao_path(nome_arquivo)
    if not os.path.exists(caminho):
        return ""
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def salvar_producao(nome_arquivo: str, conteudo: str) -> bool:
    """Sobrescreve o conteúdo de um arquivo .txt."""
    caminho = _automacao_path(nome_arquivo)
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar producao: {e}")
        return False


def criar_cabecalho(nome_arquivo: str, medico: str, data: str) -> dict:
    """Adiciona cabeçalho se o último for diferente. Retorna dict com status."""
    caminho = _automacao_path(nome_arquivo)
    novo_header = f"PROFISSIONAL: {medico.upper()} | DATA: {data}"

    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)

        # Verifica se o último cabeçalho no arquivo é igual ao novo
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            for linha in reversed(linhas):
                linha_limpa = linha.strip()
                if not linha_limpa or not linha_limpa.startswith("PROFISSIONAL:"):
                    continue
                if linha_limpa == novo_header:
                    logger.info(f"Cabecalho ja existe, pulando: {novo_header}")
                    return {"criado": False, "header": novo_header}
                break

        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"{novo_header}\n")
        return {"criado": True, "header": novo_header}
    except Exception as e:
        logger.error(f"Erro ao criar cabecalho: {e}")
        return {"criado": False, "header": "", "erro": str(e)}


def adicionar_paciente(nome_arquivo: str, documento: str) -> bool:
    doc_limpo = documento.strip()
    caminho = _automacao_path(nome_arquivo)
    try:
        pacientes_no_lote = 0
        ultimo_cabecalho = ""
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            for linha in reversed(linhas):
                linha_limpa = linha.strip()
                if not linha_limpa:
                    continue
                if linha_limpa.startswith("PROFISSIONAL:"):
                    ultimo_cabecalho = linha_limpa
                    break
                else:
                    pacientes_no_lote += 1
        with open(caminho, "a", encoding="utf-8") as f:
            if pacientes_no_lote >= 99 and ultimo_cabecalho:
                f.write(f"\n{ultimo_cabecalho}\n")
            f.write(f"{doc_limpo}\n")
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar paciente: {e}")
        return False


# ── 2. BUSCA DE PACIENTES (hospital.db) ─────────────────────


def buscar_pacientes(termo: str) -> list[dict]:
    if not termo or len(termo) < 2:
        return []
    termo = termo.upper().strip()
    try:
        conn = _get_legacy_conn()
        cur = conn.cursor()
        doc = _apenas_numeros(termo)
        resultados: list[dict] = []

        # Se tem letras, busca por nome
        if termo != doc:
            cur.execute(
                "SELECT cpf, sus, nome, dn FROM pacientes WHERE nome LIKE ? LIMIT 50",
                (f"%{termo}%",),
            )
            for row in cur.fetchall():
                resultados.append(dict(row))

        # Se tem números (parcial ou completo), busca CPF/SUS com LIKE
        if len(doc) >= 3:
            if len(doc) in (11, 15):
                # Tenta exato primeiro
                cur.execute(
                    "SELECT cpf, sus, nome, dn FROM pacientes WHERE cpf = ? OR sus = ? LIMIT 1",
                    (doc, doc),
                )
                row = cur.fetchone()
                if row:
                    row_dict = dict(row)
                    if row_dict not in resultados:
                        resultados.insert(0, row_dict)
            # Busca parcial
            cur.execute(
                "SELECT cpf, sus, nome, dn FROM pacientes WHERE cpf LIKE ? OR sus LIKE ? LIMIT 50",
                (f"{doc}%", f"{doc}%"),
            )
            for row in cur.fetchall():
                row_dict = dict(row)
                if row_dict not in resultados:
                    resultados.append(row_dict)

        conn.close()
        return resultados
    except Exception as e:
        logger.error(f"Erro ao buscar pacientes: {e}")
        return []


# ── 3. TRIAGEM ──────────────────────────────────────────────


def triagem_processar(conteudo: str) -> dict:
    """Extrai CPF/SUS de texto bagunçado."""
    caminho = _automacao_path("cpf_sus.txt")
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
    except Exception as e:
        return {"documentos": [], "total": 0, "erro": str(e)}

    documentos: list[str] = []
    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        sus_encontrado = ""
        cpf_encontrado = ""
        for parte in linha.split():
            num = _apenas_numeros(parte)
            if len(num) == 15 and _valida_cns(num):
                sus_encontrado = num
            elif len(num) == 11 and _valida_cpf(num):
                cpf_encontrado = num
        if sus_encontrado:
            documentos.append(sus_encontrado)
        elif cpf_encontrado:
            documentos.append(cpf_encontrado)

    return {"documentos": documentos, "total": len(documentos)}


def triagem_gerar_lotes(conteudo: str, enfermeiros: str, data: str) -> dict:
    """Extrai CPF/SUS, valida contra Firebird, gera 1 .txt com cabeçalhos por enfermeiro."""
    # 1. Extrai documentos
    extraidos = triagem_processar(conteudo)
    if extraidos.get("erro"):
        return {"arquivo": "", "total_extraidos": 0, "total_validos": 0, "total_invalidos": 0, "lotes": [], "erro": extraidos["erro"]}

    # 2. Carrega documentos válidos do Firebird
    doc_validos = _carregar_documentos_firebird()

    # 3. Separa válidos e inválidos
    validos: list[str] = []
    for doc in extraidos["documentos"]:
        if doc in doc_validos:
            validos.append(doc)

    # 4. Distribui entre enfermeiros (sequencial, 99 por batch)
    nomes = [n.strip().upper() for n in enfermeiros.split(",") if n.strip()]
    if not nomes:
        invalidos = [d for d in extraidos["documentos"] if d not in doc_validos]
        return {"arquivo": "", "total_extraidos": len(extraidos["documentos"]), "total_validos": 0, "total_invalidos": len(invalidos), "lotes": [], "erro": "Nenhum enfermeiro informado"}

    data_arq = data.replace("/", "-")
    arquivo = f"{data_arq}-ENFERMEIROS.txt"
    caminho = _automacao_path(arquivo)
    lotes: list[dict] = []
    idx = 0

    with open(caminho, "w", encoding="utf-8") as f:
        for nome in nomes:
            if idx >= len(validos):
                break
            fim = min(idx + 99, len(validos))
            pacientes_lote = validos[idx:fim]
            f.write(f"PROFISSIONAL: {nome} | DATA: {data}\n")
            for p in pacientes_lote:
                f.write(f"{p}\n")
            lotes.append({"enfermeiro": nome, "pacientes": len(pacientes_lote)})
            idx = fim

    invalidos = [d for d in extraidos["documentos"] if d not in doc_validos]
    return {
        "arquivo": arquivo,
        "total_extraidos": len(extraidos["documentos"]),
        "total_validos": len(validos),
        "total_invalidos": len(invalidos),
        "lotes": lotes,
        "erro": "",
    }


# ── 4. ROBÔ RPA (preparação) ──────────────────────────────


def _parse_header(linha: str) -> tuple[str, str]:
    """Extrai médico e data de uma linha 'PROFISSIONAL: ... | DATA: ...'."""
    medico = ""
    data = ""
    partes = linha.split("|")
    if len(partes) >= 1:
        medico = partes[0].replace("PROFISSIONAL:", "").strip()
    if len(partes) >= 2:
        data = partes[1].replace("DATA:", "").strip()
    return medico, data


def robo_preparar(nome_arquivo: str) -> dict:
    """Prepara lotes para RPA: lê .txt, valida apenas contra Firebird (BPAMAG.GDB)."""
    caminho = _automacao_path(nome_arquivo)
    if not os.path.exists(caminho):
        return {"lotes": [], "erro": "Arquivo nao encontrado."}

    # Carrega documentos válidos apenas do Firebird
    doc_validos: set[str] = set()
    try:
        doc_validos = _carregar_documentos_firebird()
    except Exception as e:
        logger.warning(f"Erro ao carregar Firebird: {e}")

    # Parse do arquivo
    with open(caminho, "r", encoding="utf-8") as f:
        linhas = f.readlines()

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


# Cache de processos RPA em execução
_processos_rpa: dict[int, dict] = {}


def _robo_pid_valido(pid: int) -> bool:
    """Verifica se um PID está ativo sem usar psutil."""
    try:
        proc = subprocess.Popen(["tasklist", "/FI", f"PID eq {pid}", "/NH"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        out, _ = proc.communicate(timeout=5)
        return str(pid) in out.decode("utf-8", errors="ignore")
    except Exception:
        return False


def robo_executar(medico: str, data: str, procedimento: str, pacientes: list[str]) -> dict:
    """Executa o RPA (PyAutoGUI) em background. Retorna o PID."""
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
    """Verifica se o processo RPA ainda está rodando."""
    info = _processos_rpa.get(pid)
    if not info:
        return {"status": "desconhecido", "mensagem": "PID nao encontrado"}
    rodando = _robo_pid_valido(pid)
    if not rodando:
        _processos_rpa.pop(pid, None)
    return {"status": "executando" if rodando else "concluido", **info}
