from typing import Literal, Optional

from pydantic import BaseModel


# ── Profissionais / Digitação ────────────────────────────────────────────────
class ProfissionalResponse(BaseModel):
    cns: str
    nome: str
    categorias: list[str]


class PacienteBuscaResponse(BaseModel):
    sus: str
    nome: str
    dtnasc: str
    cpf: str


class CabecalhoLoteRequest(BaseModel):
    arquivo: str
    medico: str
    data: str


class AdicionarDocumentoRequest(BaseModel):
    arquivo: str
    documento: str


# ── Lotes ─────────────────────────────────────────────────────────────────────
class LoteInfo(BaseModel):
    nome: str
    tamanho: int
    modificado_em: str


class SalvarLoteRequest(BaseModel):
    conteudo: str


# ── Análise / Geração ────────────────────────────────────────────────────────
class CandidatoProfissional(BaseModel):
    cns: str
    nome: str


class GrupoAnalise(BaseModel):
    indice: int
    medico_raw: str
    data: str
    qtd_documentos: int
    profissional_status: Literal["auto", "ambiguo", "nao_encontrado"]
    cns_prof: Optional[str] = None
    nome_prof: Optional[str] = None
    categoria_status: Optional[Literal["auto", "ambiguo", "desconhecido"]] = None
    categoria: Optional[Literal["medico", "enfermeiro"]] = None
    candidatos_profissional: list[CandidatoProfissional] = []
    categorias_possiveis: list[str] = []


class AnaliseLoteResponse(BaseModel):
    arquivo: str
    grupos: list[GrupoAnalise]


class ResolucaoGrupo(BaseModel):
    indice: int
    cns_prof: str
    categoria: Literal["medico", "enfermeiro"]


class GerarLoteRequest(BaseModel):
    resolucoes: list[ResolucaoGrupo]


class GerarLoteResponse(BaseModel):
    arquivo_gerado: str
    validacao_ok: bool
    registros: int
    folhas: int
    competencia: str
    nao_encontrados: list[str]
