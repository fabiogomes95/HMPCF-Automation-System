from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PacienteBusca(BaseModel):
    cpf: str = ""
    sus: str = ""
    nome: str = ""
    dn: str = ""


class CabecalhoCreate(BaseModel):
    arquivo: str = Field(..., description="Nome do arquivo .txt")
    medico: str = Field(..., max_length=200)
    data: str = Field(..., max_length=10, description="DD/MM/AAAA")


class PacienteAdd(BaseModel):
    arquivo: str = Field(..., description="Nome do arquivo .txt")
    documento: str = Field(..., min_length=1)


class TriagemRequest(BaseModel):
    conteudo: str = Field(..., description="Texto bagunçado com CPF/SUS")


class TriagemResponse(BaseModel):
    documentos: list[str]
    total: int
    erro: Optional[str] = None


class TriagemEnfermeirosRequest(BaseModel):
    conteudo: str = Field(..., description="Texto bagunçado com CPF/SUS")
    enfermeiros: str = Field(..., description="Nomes separados por vírgula")
    data: str = Field(..., max_length=10, description="DD/MM/AAAA")


class BatchEnfermeiro(BaseModel):
    enfermeiro: str
    pacientes: int


class TriagemEnfermeirosResponse(BaseModel):
    arquivo: str
    total_extraidos: int
    total_validos: int
    total_invalidos: int
    lotes: list[BatchEnfermeiro]
    erro: str = ""


class RoboPrepararResponse(BaseModel):
    lotes: list[dict]
    erro: str = ""


class LoteInfo(BaseModel):
    medico: str
    data: str
    pacientes: list[str]
    validados: list[str]
