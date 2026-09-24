"""Digitação dos lotes do dia: busca de paciente, cabeçalho, gravar CPF,
localizar prontuário nos lotes, dividir entre enfermeiros e listar lotes."""
from datetime import datetime

import bpa_gerador as bpa

from bpa_local.cache import cache


def buscar(q: str, incluir_sus: bool) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    return bpa.buscar_pacientes_memoria(q, cache.pacientes, limite=40, incluir_sus=incluir_sus)


def cabecalho(d: dict) -> dict:
    medico = (d.get("medico") or "").strip()
    cns = (d.get("cns") or "").strip()
    data = (d.get("data") or "").strip()
    if not medico or len(data) < 10:
        return {"ok": False, "erro": "Preencha profissional e data."}
    arquivo = bpa.nome_arquivo_lote(data)
    bpa.criar_cabecalho_lote(arquivo, medico, data, cns=cns)
    # conta pacientes já gravados no arquivo (sessões anteriores do dia)
    try:
        grupos = bpa.ler_arquivo_lote(bpa.caminho_lote(arquivo))
        existentes = sum(len(g["documentos"]) for g in grupos)
    except Exception:
        existentes = 0
    return {"ok": True, "arquivo": arquivo, "existentes": existentes}


def gravar(d: dict) -> dict:
    arquivo = (d.get("arquivo") or "").strip()
    cpf = (d.get("cpf") or "").strip()
    nome = (d.get("nome") or "").strip()
    if not arquivo or not cpf:
        return {"ok": False, "erro": "Arquivo ou CPF inválido."}
    try:
        bpa.adicionar_documento_lote(arquivo, cpf)
        return {"ok": True, "nome": nome}
    except bpa.LoteError as e:
        return {"ok": False, "erro": str(e)}


def recarregar() -> dict:
    cache.carregar_tudo()
    return {"ok": True, "total": len(cache.pacientes), "erro": cache.erro, "profs": cache.profissionais}


def prontuario_buscar(q: str) -> dict:
    """Localiza em quais dias/profissionais um paciente já foi digitado."""
    q = q.strip()
    if len(q) < 3:
        return {"ok": True, "pacientes": []}
    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}
    try:
        candidatos = bpa.buscar_paciente_cadcns_live(con, q)
    finally:
        con.close()

    # Lotes antigos (ex: MAIO/) foram digitados por SUS, não por CPF — a
    # triagem só passou a exigir CPF depois (ver extrair_documentos_validos).
    # Pra achar ocorrência em qualquer época, busca pelos dois documentos do
    # paciente e depois junta o resultado de cada um.
    todos_documentos: set[str] = set()
    docs_por_candidato: list[set[str]] = []
    for c in candidatos:
        docs = {d for d in (c.get("cpf"), c.get("sus")) if d}
        docs_por_candidato.append(docs)
        todos_documentos |= docs

    ocorrencias_por_doc = bpa.buscar_documentos_nos_lotes(todos_documentos)

    pacientes = []
    for c, docs in zip(candidatos, docs_por_candidato):
        ocorrencias = [oc for d in docs for oc in ocorrencias_por_doc.get(d, [])]
        ocorrencias.sort(key=lambda o: datetime.strptime(o["data"], "%d/%m/%Y"), reverse=True)
        pacientes.append({**c, "ocorrencias": ocorrencias})
    return {"ok": True, "pacientes": pacientes}


def enfermeiros_dividir(d: dict) -> dict:
    """Divide os CPFs já digitados pros médicos do dia entre os enfermeiros."""
    data = (d.get("data") or "").strip()
    enfermeiros = d.get("enfermeiros") or []

    if len(data) < 10:
        return {"ok": False, "erro": "Informe a data (DD/MM/AAAA)."}
    if not enfermeiros:
        return {"ok": False, "erro": "Selecione ao menos um enfermeiro."}

    arquivo = bpa.nome_arquivo_lote(data)
    caminho = bpa.caminho_lote(arquivo)
    try:
        grupos = bpa.ler_arquivo_lote(caminho)
    except bpa.LoteError as e:
        return {"ok": False, "erro": str(e)}

    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}

    try:
        # Descarta qualquer divisão de enfermeiros já feita antes nesse dia
        # (refazer não deve duplicar) e junta só os CPFs vindos de médico.
        grupos_medico: list[dict] = []
        documentos: list[str] = []
        for g in grupos:
            cns_raw = (g.get("cns") or "").strip()
            categoria = "medico"
            if cns_raw:
                cat, auto = bpa.detectar_categoria(con, cns_raw)
                if auto and cat == "enfermeiro":
                    categoria = "enfermeiro"
            if categoria == "enfermeiro":
                continue
            grupos_medico.append(g)
            documentos.extend(g["documentos"])

        if not documentos:
            return {"ok": False, "erro": "Nenhum CPF de médico digitado nesse dia ainda."}

        distribuicao = bpa.dividir_por_profissionais(documentos, enfermeiros)

        novos_grupos = []
        resumo = []
        for enf in enfermeiros:
            docs_enf = distribuicao.get(enf["cns"], [])
            if not docs_enf:
                continue
            novos_grupos.append({
                "medico_raw": enf["nome"], "cns": enf["cns"], "data": data, "documentos": docs_enf,
            })
            resumo.append({"nome": enf["nome"], "cns": enf["cns"], "qtd": len(docs_enf)})

        bpa.regravar_lote(arquivo, grupos_medico + novos_grupos)

        return {"ok": True, "arquivo": arquivo, "total": len(documentos), "distribuicao": resumo}
    finally:
        con.close()


def lotes() -> list[dict]:
    return [
        {
            "nome": lote["nome"],
            "tamanho": lote["tamanho"],
            "modificado_em": lote["modificado_em"].strftime("%d/%m/%Y %H:%M"),
        }
        for lote in bpa.listar_lotes()
    ]


def lote(arquivo: str) -> dict:
    """Conteúdo de um lote do dia, bloco a bloco, com o nome de cada paciente
    (pelo cache do Firebird) — a tela mostra os gravados e, na aba
    Enfermeiros, quantos CPFs os médicos já digitaram."""
    arquivo = (arquivo or "").strip()
    if not arquivo:
        return {"ok": False, "erro": "Informe o lote."}
    try:
        grupos = bpa.ler_arquivo_lote(bpa.caminho_lote(arquivo))
    except bpa.LoteError as e:
        return {"ok": False, "erro": str(e)}

    nomes = {}
    for p in cache.pacientes:
        if p.get("cpf"):
            nomes[p["cpf"]] = p["nome"]
        if p.get("sus"):
            nomes.setdefault(p["sus"], p["nome"])
    categorias = {p["cns"]: p["categoria"] for p in cache.profissionais}

    blocos = []
    for g in grupos:
        cns = (g.get("cns") or "").strip()
        blocos.append({
            "profissional": g.get("medico_raw", ""),
            "cns": cns,
            "categoria": categorias.get(cns.zfill(15), categorias.get(cns, "")),
            "data": g.get("data", ""),
            "pacientes": [{"doc": d, "nome": nomes.get(d, "")} for d in g["documentos"]],
        })
    return {"ok": True, "arquivo": arquivo, "blocos": blocos}
