from __future__ import annotations

import os
import subprocess
import tempfile
from logging import getLogger
from pathlib import Path

try:
    import firebirdsql
except ImportError:
    firebirdsql = None  # type: ignore[assignment]

logger = getLogger(__name__)

# ── Constantes ──
FB_PATH = Path(r"C:\BPA\BPAMAG.GDB")
FB_USER = "SYSDBA"
FB_PASS = "masterkey"
FB_CONNECT_ARGS = dict(
    host="localhost",
    database=str(FB_PATH),
    user=FB_USER,
    password=FB_PASS,
    charset="WIN1252",
)

ISQL_PATH = Path(r"C:\Program Files (x86)\Firebird\Firebird_1_5\bin\isql.exe")


def get_firebird_conn():
    if firebirdsql is None:
        raise ImportError("firebirdsql nao instalado")
    if not FB_PATH.exists():
        raise FileNotFoundError(f"BPAMAG.GDB nao encontrado: {FB_PATH}")
    return firebirdsql.connect(**FB_CONNECT_ARGS)


def isql_query(sql: str) -> str:
    if not ISQL_PATH.exists() or not FB_PATH.exists():
        logger.warning("isql ou BPAMAG.GDB nao encontrado")
        return ""
    sql_file = os.path.join(tempfile.gettempdir(), "fb_query.txt")
    try:
        with open(sql_file, "w", encoding="ascii") as f:
            f.write(sql)
        resultado = subprocess.run(
            [str(ISQL_PATH), "-q", str(FB_PATH), "-u", FB_USER, "-p", FB_PASS, "-i", sql_file],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return resultado.stdout + resultado.stderr
    except Exception as e:
        logger.error("isql_query: %s", e)
        return str(e)
    finally:
        try:
            os.remove(sql_file)
        except Exception:
            pass


def carregar_documentos_firebird() -> set[str]:
    documentos: set[str] = set()
    if not ISQL_PATH.exists() or not FB_PATH.exists():
        return documentos

    sql_file = os.path.join(tempfile.gettempdir(), "fb_query_cpf.txt")
    try:
        with open(sql_file, "w", encoding="ascii") as f:
            f.write("SELECT NUM_CPF, CNS FROM CADCNS;\n")
        resultado = subprocess.run(
            [str(ISQL_PATH), "-q", str(FB_PATH), "-u", FB_USER, "-p", FB_PASS, "-i", sql_file],
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
                nums = "".join(filter(str.isdigit, p))
                if len(nums) in (11, 15):
                    documentos.add(nums)
    except Exception as e:
        logger.error("carregar_documentos_firebird: %s", e)
    finally:
        try:
            os.remove(sql_file)
        except Exception:
            pass

    logger.info("carregar_documentos_firebird: %d documentos carregados", len(documentos))
    return documentos
