from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.modules.integracao import service as integracao
from app.modules.integracao.schemas import (
    ExecutarBackup,
    ExecutarConverterCSV,
    ExecutarCorrigirNulls,
    ExecutarExportarBPA,
    ExecutarImportarCSV,
    ExecutarLimparDuplicatas,
    ExecutarSincronizarContingencia,
    ExecutarSincronizarFirebird,
    BackupInfo,
    IntegracaoResponse,
)

router = APIRouter(prefix="/integracao", tags=["integracao"])


@router.post("/exportar-bpa")
async def exportar_bpa(dados: ExecutarExportarBPA) -> IntegracaoResponse:
    saida = integracao.exportar_bpa(dados.mes_ano, dados.caminho_salvar)
    return IntegracaoResponse(saida=saida)


@router.post("/exportar-bpa/download")
async def exportar_bpa_download(dados: ExecutarExportarBPA) -> PlainTextResponse:
    try:
        conteudo, erros, resumo = integracao.gerar_conteudo_bpa(dados.mes_ano)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    filename = dados.caminho_salvar or "BPA_EXPORTADO_SQLITE.txt"
    return PlainTextResponse(
        conteudo,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/importar-csv")
async def importar_csv(dados: ExecutarImportarCSV) -> IntegracaoResponse:
    saida = integracao.importar_csv(dados.separador, dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/converter-csv")
async def converter_csv(dados: ExecutarConverterCSV) -> IntegracaoResponse:
    saida = integracao.converter_csv(dados.caminho_arquivo, dados.caminho_salvar)
    return IntegracaoResponse(saida=saida)


@router.post("/sincronizar-contingencia")
async def sincronizar_contingencia(dados: ExecutarSincronizarContingencia) -> IntegracaoResponse:
    saida = integracao.sincronizar_contingencia(dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/sincronizar-firebird")
async def sincronizar_firebird() -> IntegracaoResponse:
    saida = integracao.sincronizar_firebird()
    return IntegracaoResponse(saida=saida)


@router.post("/corrigir-nulls")
async def corrigir_nulls(dados: ExecutarCorrigirNulls) -> IntegracaoResponse:
    saida = integracao.corrigir_nulls(dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/limpar-duplicatas")
async def limpar_duplicatas(dados: ExecutarLimparDuplicatas) -> IntegracaoResponse:
    saida = integracao.limpar_duplicatas(dados.caminho_arquivo)
    return IntegracaoResponse(saida=saida)


@router.post("/backup")
async def backup(dados: ExecutarBackup) -> IntegracaoResponse:
    result = integracao.fazer_backup(dados.caminho_arquivo, "manual")
    if result.get("status") == "ok":
        return IntegracaoResponse(saida=f"Backup criado: {result['arquivo']}")
    raise HTTPException(status_code=400, detail=result.get("mensagem", "Erro desconhecido"))


@router.get("/backups")
async def listar_backups() -> list[BackupInfo]:
    backups = integracao.listar_backups()
    return [BackupInfo(**b) for b in backups]
