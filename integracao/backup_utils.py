"""
BACKUP_UTILS.PY — Backup automático antes de operações destrutivas
==================================================================
Cria cópias timestamps dos bancos antes de sincronizações, correções, etc.
Os backups ficam em /backups/ na raiz do projeto.
"""

import os
import shutil
from datetime import datetime
from logging_setup import logger

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(SRC_DIR, "backups")


def _garantir_pasta() -> None:
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)


def fazer_backup(caminho_arquivo: str, prefixo: str = "") -> str | None:
    if not caminho_arquivo or not os.path.exists(caminho_arquivo):
        logger.warning(f"Backup ignorado — arquivo nao encontrado: {caminho_arquivo}")
        return None

    _garantir_pasta()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_base = os.path.basename(caminho_arquivo)
    nome_backup = f"{prefixo}_{timestamp}_{nome_base}" if prefixo else f"{timestamp}_{nome_base}"
    destino = os.path.join(BACKUP_DIR, nome_backup)

    try:
        shutil.copy2(caminho_arquivo, destino)
        logger.info(f"Backup criado: {destino}")
        return destino
    except Exception as e:
        logger.error(f"Erro ao criar backup de {caminho_arquivo}: {e}")
        return None


def listar_backups(arquivo_original: str = "") -> list[dict]:
    _garantir_pasta()
    backups = []
    padrao = os.path.basename(arquivo_original) if arquivo_original else ""

    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if padrao and padrao not in f:
            continue
        caminho = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(caminho):
            backups.append({
                "nome": f,
                "tamanho": os.path.getsize(caminho),
                "data": datetime.fromtimestamp(os.path.getmtime(caminho)).isoformat(),
            })

    return backups
