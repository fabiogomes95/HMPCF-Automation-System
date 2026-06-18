from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.schemas.bpa import (
    AdicionarDocumentoRequest,
    AnaliseLoteResponse,
    CabecalhoLoteRequest,
    GerarLoteRequest,
    GerarLoteResponse,
    LoteInfo,
    PacienteBuscaResponse,
    ProfissionalResponse,
    SalvarLoteRequest,
)
from app.services import bpa_service

router = APIRouter()


# ── Profissionais / busca de pacientes (Digitação) ──────────────────────────
@router.get(
    "/profissionais",
    response_model=list[ProfissionalResponse],
    summary="Lista profissionais (CADMED) com categoria detectada via CBO",
)
async def listar_profissionais() -> list[ProfissionalResponse]:
    return await bpa_service.listar_profissionais()


@router.get(
    "/pacientes/busca",
    response_model=list[PacienteBuscaResponse],
    summary="Busca pacientes por nome/CNS/CPF no cache da CADCNS",
)
async def buscar_pacientes(
    termo: str = Query("", description="Nome, CNS ou CPF (mín. 3 caracteres)"),
) -> list[PacienteBuscaResponse]:
    return await bpa_service.buscar_pacientes_cache(termo)


@router.post(
    "/cache/atualizar",
    summary="Recarrega o cache de pacientes (CADCNS) na memória",
)
async def atualizar_cache() -> dict:
    qtd = await bpa_service.carregar_cache_pacientes()
    return {"qtd_pacientes": qtd}


@router.get(
    "/cache/status",
    summary="Status do cache de pacientes sem recarregar",
)
async def status_cache() -> dict:
    return bpa_service.status_cache()


# ── Lotes (.txt) ──────────────────────────────────────────────────────────────
@router.get(
    "/lotes",
    response_model=list[LoteInfo],
    summary="Lista os arquivos de lote disponíveis",
)
async def listar_lotes() -> list[LoteInfo]:
    return bpa_service.listar_lotes()


@router.get(
    "/lotes/{nome}",
    summary="Lê o conteúdo bruto de um lote",
)
async def ler_lote(nome: str) -> dict:
    return {"conteudo": bpa_service.ler_lote(nome)}


@router.put(
    "/lotes/{nome}",
    status_code=204,
    summary="Salva/sobrescreve o conteúdo de um lote",
)
async def salvar_lote(nome: str, data: SalvarLoteRequest) -> None:
    bpa_service.salvar_lote(nome, data.conteudo)


@router.post(
    "/lotes/cabecalho",
    status_code=204,
    summary="Adiciona um cabeçalho de bloco (PROFISSIONAL: ... | DATA: ...)",
)
async def criar_cabecalho(data: CabecalhoLoteRequest) -> None:
    bpa_service.criar_cabecalho_lote(data.arquivo, data.medico, data.data)


@router.post(
    "/lotes/documento",
    status_code=204,
    summary="Adiciona um CNS/CPF ao bloco atual (com rollover automático de 99)",
)
async def adicionar_documento(data: AdicionarDocumentoRequest) -> None:
    bpa_service.adicionar_documento_lote(data.arquivo, data.documento)


# ── Análise e geração do arquivo BPA-I ───────────────────────────────────────
@router.post(
    "/lotes/{nome}/analisar",
    response_model=AnaliseLoteResponse,
    summary="Analisa um lote: resolve profissional/categoria por grupo, sem gerar nada",
)
async def analisar_lote(nome: str) -> AnaliseLoteResponse:
    return await bpa_service.analisar_lote(nome)


@router.post(
    "/lotes/{nome}/gerar",
    response_model=GerarLoteResponse,
    summary="Gera o arquivo BPA-I final a partir das resoluções confirmadas",
)
async def gerar_lote(nome: str, data: GerarLoteRequest) -> GerarLoteResponse:
    resolucoes = [r.model_dump() for r in data.resolucoes]
    return await bpa_service.gerar_arquivo_de_lote(nome, resolucoes)


@router.get(
    "/gerar/download/{nome_arquivo}",
    summary="Baixa o arquivo BPA-I já gerado (~/Downloads)",
)
async def download_arquivo_gerado(nome_arquivo: str) -> FileResponse:
    caminho = bpa_service.caminho_arquivo_gerado(nome_arquivo)
    return FileResponse(caminho, media_type="text/plain", filename=nome_arquivo)
