from __future__ import annotations

import os
import shutil
from datetime import datetime
from logging import getLogger

from app.core.config import settings

logger = getLogger(__name__)


def _backup_pasta() -> str:
    pasta = os.path.join(os.path.dirname(settings.PROJECT_ROOT), "backups")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def fazer_backup(caminho_arquivo: str, prefixo: str = "") -> dict:
    logger.info("fazer_backup: arquivo=%s, prefixo=%s", caminho_arquivo, prefixo or "-")
    if not os.path.exists(caminho_arquivo):
        logger.error("fazer_backup: arquivo nao encontrado: %s", caminho_arquivo)
        return {"status": "erro", "mensagem": "Arquivo nao encontrado"}
    destino = _backup_pasta()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_base = os.path.basename(caminho_arquivo)
    nome_backup = f"{prefixo}_{timestamp}_{nome_base}" if prefixo else f"{timestamp}_{nome_base}"
    caminho_destino = os.path.join(destino, nome_backup)
    try:
        shutil.copy2(caminho_arquivo, caminho_destino)
        logger.info("fazer_backup: copiado para %s", caminho_destino)
        return {"status": "ok", "arquivo": caminho_destino}
    except Exception as e:
        logger.error("fazer_backup: erro: %s", e)
        return {"status": "erro", "mensagem": str(e)}


def listar_backups(arquivo_original: str = "") -> list[dict]:
    pasta = _backup_pasta()
    backups: list[dict] = []
    for f in sorted(os.listdir(pasta), reverse=True):
        if arquivo_original and arquivo_original not in f:
            continue
        caminho = os.path.join(pasta, f)
        if os.path.isfile(caminho):
            backups.append({
                "nome": f,
                "tamanho": os.path.getsize(caminho),
                "data": datetime.fromtimestamp(os.path.getmtime(caminho)).isoformat(),
            })
    return backups
