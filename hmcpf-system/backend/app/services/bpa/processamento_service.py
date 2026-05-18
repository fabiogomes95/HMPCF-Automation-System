from __future__ import annotations

from logging import getLogger

from app.database import firebird as fb
from app.repositories import producao_repository as producao_repo
from app.services.bpa.producao_service import _automacao_path
from app.services.bpa.validacao_service import apenas_numeros, valida_cns, valida_cpf

logger = getLogger(__name__)


def triagem_processar(conteudo: str) -> dict:
    caminho = _automacao_path("cpf_sus.txt")
    if not producao_repo.salvar_arquivo(caminho, conteudo):
        return {"documentos": [], "total": 0, "erro": "Erro ao salvar arquivo de triagem"}

    documentos: list[str] = []
    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        sus_encontrado = ""
        cpf_encontrado = ""
        for parte in linha.split():
            num = apenas_numeros(parte)
            if len(num) == 15 and valida_cns(num):
                sus_encontrado = num
            elif len(num) == 11 and valida_cpf(num):
                cpf_encontrado = num
        if sus_encontrado:
            documentos.append(sus_encontrado)
        elif cpf_encontrado:
            documentos.append(cpf_encontrado)

    return {"documentos": documentos, "total": len(documentos)}


def triagem_gerar_lotes(conteudo: str, enfermeiros: str, data: str) -> dict:
    extraidos = triagem_processar(conteudo)
    if extraidos.get("erro"):
        return {"arquivo": "", "total_extraidos": 0, "total_validos": 0, "total_invalidos": 0, "lotes": [], "erro": extraidos["erro"]}

    doc_validos = fb.carregar_documentos_firebird()
    validos = [d for d in extraidos["documentos"] if d in doc_validos]

    nomes = [n.strip().upper() for n in enfermeiros.split(",") if n.strip()]
    if not nomes:
        invalidos = [d for d in extraidos["documentos"] if d not in doc_validos]
        return {"arquivo": "", "total_extraidos": len(extraidos["documentos"]), "total_validos": 0, "total_invalidos": len(invalidos), "lotes": [], "erro": "Nenhum enfermeiro informado"}

    data_arq = data.replace("/", "-")
    arquivo = f"{data_arq}-ENFERMEIROS.txt"
    caminho = _automacao_path(arquivo)
    lotes = producao_repo.escrever_lotes(caminho, nomes, validos, data)

    invalidos = [d for d in extraidos["documentos"] if d not in doc_validos]
    return {
        "arquivo": arquivo,
        "total_extraidos": len(extraidos["documentos"]),
        "total_validos": len(validos),
        "total_invalidos": len(invalidos),
        "lotes": lotes,
        "erro": "",
    }
