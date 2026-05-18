from __future__ import annotations

from pydantic import BaseModel, Field


class ExecutarExportarBPA(BaseModel):
    mes_ano: str = Field("", description="Mês/Ano (MMAAAA) para filtrar")
    caminho_salvar: str = Field("", description="Onde salvar o TXT")


class ExecutarImportarCSV(BaseModel):
    separador: str = Field(";", description="Delimitador do CSV")
    caminho_arquivo: str = Field("", description="Caminho do CSV")


class ExecutarConverterCSV(BaseModel):
    caminho_arquivo: str = Field("", description="Caminho do CSV antigo")
    caminho_salvar: str = Field("", description="Onde salvar o TXT")


class ExecutarSincronizarContingencia(BaseModel):
    caminho_arquivo: str = Field("", description="Caminho do CSV de contingência")


class ExecutarSincronizarFirebird(BaseModel):
    mes_ano: str = Field("", description="Opcional")
    caminho_salvar: str = Field("", description="Opcional")


class ExecutarCorrigirNulls(BaseModel):
    caminho_arquivo: str = Field("", description="Opcional (não usado)")


class ExecutarLimparDuplicatas(BaseModel):
    caminho_arquivo: str = Field("", description="Opcional (não usado)")


class ExecutarBackup(BaseModel):
    caminho_arquivo: str = Field(..., description="Caminho do arquivo para backup")


class IntegracaoResponse(BaseModel):
    saida: str


class BackupInfo(BaseModel):
    nome: str
    tamanho: int
    data: str
