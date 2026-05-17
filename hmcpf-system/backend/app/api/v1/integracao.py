from __future__ import annotations

from fastapi import APIRouter

from app.modules.integracao import service as integracao
from app.modules.integracao.schemas import IntegracaoExecutarRequest, IntegracaoResponse

router = APIRouter(prefix="/integracao", tags=["integracao"])


@router.post("/exportar-bpa")
async def exportar_bpa(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    saida = integracao.exportar_bpa(dados.mes_ano, dados.caminho_salvar)
    return IntegracaoResponse(saida=saida)


@router.post("/importar-csv")
async def importar_csv(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    saida = integracao.importar_csv(dados.separador, dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/converter-csv")
async def converter_csv(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    saida = integracao.converter_csv(dados.caminho_arquivo, dados.caminho_salvar)
    return IntegracaoResponse(saida=saida)


@router.post("/sincronizar-firebird")
async def sincronizar_firebird(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    saida = integracao.sincronizar_firebird(dados.mes_ano, dados.caminho_salvar)
    return IntegracaoResponse(saida=saida)


@router.post("/corrigir-nulls")
async def corrigir_nulls(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    saida = integracao.corrigir_nulls(dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/limpar-duplicatas")
async def limpar_duplicatas(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    saida = integracao.limpar_duplicatas(dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/backup")
async def backup(dados: IntegracaoExecutarRequest) -> IntegracaoResponse:
    caminho = dados.caminho_arquivo or ""
    if not caminho:
        return IntegracaoResponse(saida="Informe caminho_arquivo para fazer backup.")
    result = integracao.fazer_backup(caminho, "manual")
    if result.get("status") == "ok":
        return IntegracaoResponse(saida=f"Backup criado: {result['arquivo']}")
    return IntegracaoResponse(saida=f"Erro: {result.get('mensagem')}")


@router.get("/backups")
async def listar_backups() -> list[dict]:
    return integracao.listar_backups()
