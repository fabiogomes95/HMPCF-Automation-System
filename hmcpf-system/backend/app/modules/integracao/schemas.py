from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class IntegracaoExecutarRequest(BaseModel):
    """Parâmetros opcionais para cada ferramenta."""
    mes_ano: str = ""
    caminho_arquivo: str = ""
    caminho_salvar: str = ""
    separador: str = ";"


class IntegracaoResponse(BaseModel):
    saida: str
    erro: str = ""


class BackupInfo(BaseModel):
    nome: str
    tamanho: int
    data: str
