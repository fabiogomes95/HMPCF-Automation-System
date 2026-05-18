from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.database.legacy import get_legacy_conn
from app.repositories import paciente_repository as paciente_repo
from app.repositories import producao_repository as producao_repo

logger = getLogger(__name__)

_AUTOMACAO_DIR: Path = settings.PROJECT_ROOT.parent / "automacao"


def _automacao_path(arquivo: str = "") -> str:
    return str(_AUTOMACAO_DIR / (arquivo or ""))


def listar_producoes() -> list[str]:
    return producao_repo.listar_arquivos(_automacao_path())


def ler_producao(nome_arquivo: str) -> str:
    return producao_repo.ler_arquivo(_automacao_path(nome_arquivo))


def salvar_producao(nome_arquivo: str, conteudo: str) -> bool:
    return producao_repo.salvar_arquivo(_automacao_path(nome_arquivo), conteudo)


def criar_cabecalho(nome_arquivo: str, medico: str, data: str) -> dict:
    caminho = _automacao_path(nome_arquivo)
    novo_header = f"PROFISSIONAL: {medico.upper()} | DATA: {data}"
    try:
        ultimo = producao_repo.ultimo_cabecalho(caminho)
        if ultimo == novo_header:
            logger.info(f"Cabecalho ja existe, pulando: {novo_header}")
            return {"criado": False, "header": novo_header}
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        producao_repo.anexar_linha(caminho, novo_header)
        return {"criado": True, "header": novo_header}
    except Exception as e:
        logger.error(f"Erro ao criar cabecalho: {e}")
        return {"criado": False, "header": "", "erro": str(e)}


def adicionar_paciente(nome_arquivo: str, documento: str) -> bool:
    doc_limpo = documento.strip()
    caminho = _automacao_path(nome_arquivo)
    try:
        pacientes_no_lote = producao_repo.contar_pacientes_abaixo_do_cabecalho(caminho)
        ultimo_cabecalho = producao_repo.ultimo_cabecalho(caminho) or ""
        if pacientes_no_lote >= 99 and ultimo_cabecalho:
            producao_repo.anexar_linha(caminho, f"\n{ultimo_cabecalho}")
        producao_repo.anexar_linha(caminho, doc_limpo)
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar paciente: {e}")
        return False


def _parse_header(linha: str) -> tuple[str, str]:
    medico = ""
    data = ""
    partes = linha.split("|")
    if len(partes) >= 1:
        medico = partes[0].replace("PROFISSIONAL:", "").strip()
    if len(partes) >= 2:
        data = partes[1].replace("DATA:", "").strip()
    return medico, data


def buscar_pacientes(termo: str) -> list[dict]:
    if not termo or len(termo) < 2:
        return []
    try:
        conn = get_legacy_conn()
        try:
            return paciente_repo.buscar_por_termo(conn, termo)
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Erro ao buscar pacientes: {e}")
        return []
