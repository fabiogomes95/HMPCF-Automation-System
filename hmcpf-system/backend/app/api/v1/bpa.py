from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.modules.bpa import service as bpa_service
from pydantic import BaseModel

from app.modules.bpa.schemas import (
    CabecalhoCreate,
    PacienteAdd,
    PacienteBusca,
    TriagemEnfermeirosRequest,
    TriagemEnfermeirosResponse,
    TriagemRequest,
    TriagemResponse,
    RoboPrepararResponse,
)


class RoboExecutarRequest(BaseModel):
    medico: str
    data: str
    procedimento: str = "0301060029"
    pacientes: list[str]

router = APIRouter(prefix="/bpa", tags=["bpa"])


# ── PRODUÇÕES (arquivos .txt) ──────────────────────────────


@router.get("/producoes")
async def listar_producoes() -> list[str]:
    """Lista arquivos .txt da pasta automacao/."""
    return bpa_service.listar_producoes()


@router.get("/producoes/{nome_arquivo}")
async def ler_producao(nome_arquivo: str) -> str:
    """Lê conteúdo de um arquivo .txt."""
    conteudo = bpa_service.ler_producao(nome_arquivo)
    if not conteudo:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado ou vazio")
    return conteudo


@router.put("/producoes/{nome_arquivo}")
async def salvar_producao(nome_arquivo: str, dados: dict) -> dict:
    """Sobrescreve conteúdo de um arquivo .txt."""
    conteudo = dados.get("conteudo", "")
    ok = bpa_service.salvar_producao(nome_arquivo, conteudo)
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao salvar arquivo")
    return {"status": "ok"}


@router.post("/producoes/cabecalho")
async def criar_cabecalho(dados: CabecalhoCreate) -> dict:
    """Adiciona cabeçalho de lote (médico + data) num arquivo.
    Se o último cabeçalho for igual, não duplica."""
    resultado = bpa_service.criar_cabecalho(dados.arquivo, dados.medico, dados.data)
    if resultado.get("erro"):
        raise HTTPException(status_code=500, detail=resultado["erro"])
    return {
        "status": "ok",
        "criado": resultado["criado"],
        "header": resultado["header"],
        "arquivo": dados.arquivo,
    }


@router.post("/producoes/{nome_arquivo}/paciente")
async def adicionar_paciente(nome_arquivo: str, dados: PacienteAdd) -> dict:
    """Adiciona documento de paciente ao lote."""
    ok = bpa_service.adicionar_paciente(nome_arquivo, dados.documento)
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao adicionar paciente")
    return {"status": "ok"}


# ── BUSCA DE PACIENTES ────────────────────────────────────


@router.get("/pacientes")
async def buscar_pacientes(
    termo: str = Query(..., min_length=2),
) -> list[PacienteBusca]:
    """Busca pacientes no hospital.db por nome, CPF ou SUS."""
    return bpa_service.buscar_pacientes(termo)


# ── TRIAGEM ────────────────────────────────────────────────


@router.post("/triagem", response_model=TriagemResponse)
async def triagem(dados: TriagemRequest) -> dict:
    """Extrai CPF/SUS de texto bagunçado."""
    return bpa_service.triagem_processar(dados.conteudo)


@router.post("/triagem/enfermeiros", response_model=TriagemEnfermeirosResponse)
async def triagem_enfermeiros(dados: TriagemEnfermeirosRequest) -> dict:
    """Extrai CPF/SUS, valida contra Firebird e gera lotes para enfermeiros."""
    return bpa_service.triagem_gerar_lotes(dados.conteudo, dados.enfermeiros, dados.data)


# ── ROBÔ RPA ──────────────────────────────────────────────


@router.post("/robo/preparar", response_model=RoboPrepararResponse)
async def robo_preparar(dados: dict) -> dict:
    """Prepara lotes para o RPA: lê .txt, valida contra hospital.db."""
    nome_arquivo = dados.get("arquivo", "")
    if not nome_arquivo:
        raise HTTPException(status_code=422, detail="Campo 'arquivo' é obrigatório")
    return bpa_service.robo_preparar(nome_arquivo)


@router.post("/robo/executar")
async def robo_executar(dados: RoboExecutarRequest) -> dict:
    """Executa o RPA (PyAutoGUI) em background na máquina física."""
    return bpa_service.robo_executar(dados.medico, dados.data, dados.procedimento, dados.pacientes)


@router.get("/robo/status/{pid}")
async def robo_status(pid: int) -> dict:
    """Verifica se um processo RPA ainda está rodando."""
    return bpa_service.robo_status(pid)
