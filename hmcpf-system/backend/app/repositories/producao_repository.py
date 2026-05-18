from __future__ import annotations

import glob
import os
from logging import getLogger
from typing import Optional

logger = getLogger(__name__)


def listar_arquivos(diretorio: str) -> list[str]:
    pattern = os.path.join(diretorio, "*.txt")
    arquivos = glob.glob(pattern)
    nomes = [os.path.basename(a) for a in arquivos]
    nomes.sort(reverse=True)
    nomes = [n for n in nomes if not n.startswith("cpf_sus")]
    return nomes


def ler_arquivo(caminho: str) -> str:
    if not os.path.exists(caminho):
        return ""
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def salvar_arquivo(caminho: str, conteudo: str) -> bool:
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return True
    except Exception as e:
        logger.error("Erro ao salvar arquivo: %s", e)
        return False


def ultimo_cabecalho(caminho: str) -> Optional[str]:
    if not os.path.exists(caminho):
        return None
    with open(caminho, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    for linha in reversed(linhas):
        linha_limpa = linha.strip()
        if linha_limpa.startswith("PROFISSIONAL:"):
            return linha_limpa
    return None


def contar_pacientes_abaixo_do_cabecalho(caminho: str) -> int:
    if not os.path.exists(caminho):
        return 0
    with open(caminho, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    count = 0
    for linha in reversed(linhas):
        linha_limpa = linha.strip()
        if not linha_limpa:
            continue
        if linha_limpa.startswith("PROFISSIONAL:"):
            break
        count += 1
    return count


def anexar_linha(caminho: str, linha: str) -> None:
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"{linha}\n")


def escrever_lotes(caminho: str, nomes: list[str], validos: list[str], data: str) -> list[dict]:
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
    return lotes


def ler_linhas(caminho: str) -> list[str]:
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        return f.readlines()
