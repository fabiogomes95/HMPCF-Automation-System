"""
Serviço BPA — ponte entre a API web (assíncrona) e a lógica síncrona de
Firebird/geração do arquivo BPA-I (app/services/bpa_gerador.py).

Três frentes, espelhando o que o painel antigo (legado/) fazia em 3 telas
separadas — Triagem, Digitação e Geração — mas agora num fluxo único:
  1. Cache de pacientes da CADCNS em memória, pra busca instantânea na
     Digitação (Firebird é lento se consultado a cada tecla digitada).
  2. Leitura/escrita dos arquivos de lote (.txt) em BPA_LOTES_DIR.
  3. Análise (resolução de profissional/categoria sem ambiguidade) e
     geração do arquivo BPA-I final a partir de um lote.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.services import bpa_gerador as bpa

try:
    from fastapi.concurrency import run_in_threadpool
except ImportError:  # pragma: no cover
    import asyncio

    async def run_in_threadpool(fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)


# ── Cache de pacientes (CADCNS) em memória ──────────────────────────────────
_cache_pacientes: list[dict] = []
_cache_carregado_em: float | None = None


def _carregar_cache_sync() -> list[dict]:
    con = bpa.conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS")
        pacientes = []
        for cns, nome, dtnasc, cpf in cur.fetchall():
            dn_raw = str(dtnasc or "").strip()
            dtnasc_fmt = f"{dn_raw[6:8]}/{dn_raw[4:6]}/{dn_raw[0:4]}" if len(dn_raw) == 8 else ""
            pacientes.append({
                "sus": str(cns or "").strip(),
                "nome": str(nome or "").strip().upper(),
                "dtnasc": dtnasc_fmt,
                "cpf": str(cpf or "").strip(),
            })
        return pacientes
    finally:
        con.close()


async def carregar_cache_pacientes() -> int:
    global _cache_pacientes, _cache_carregado_em
    _cache_pacientes = await run_in_threadpool(_carregar_cache_sync)
    _cache_carregado_em = time.time()
    return len(_cache_pacientes)


async def buscar_pacientes_cache(termo: str) -> list[dict]:
    if not _cache_pacientes:
        await carregar_cache_pacientes()

    if not termo:
        return _cache_pacientes[:50]

    termo = termo.upper().strip()
    resultados = []
    for p in _cache_pacientes:
        if termo in p["nome"] or termo in p["sus"] or termo in p["cpf"]:
            resultados.append(p)
            if len(resultados) == 50:
                break
    return resultados


def status_cache() -> dict:
    return {
        "qtd_pacientes": len(_cache_pacientes),
        "carregado_em": (
            datetime.fromtimestamp(_cache_carregado_em).isoformat() if _cache_carregado_em else None
        ),
    }


# ── Profissionais (para o seletor de Digitação) ─────────────────────────────
def _listar_profissionais_sync() -> list[dict]:
    con = bpa.conectar()
    try:
        profissionais = bpa.listar_profissionais(con)
        mapa = bpa.mapa_categorias_por_profissional(con)
        return [
            {
                "cns": cns_raw.zfill(15),
                "nome": nome.upper(),
                "categorias": sorted(mapa.get(cns_raw, set())),
            }
            for cns_raw, nome in profissionais
        ]
    finally:
        con.close()


async def listar_profissionais() -> list[dict]:
    return await run_in_threadpool(_listar_profissionais_sync)


# ── Arquivos de lote ─────────────────────────────────────────────────────────
def _caminho_lote(nome_arquivo: str) -> str:
    """Resolve o caminho do lote dentro de BPA_LOTES_DIR, bloqueando path traversal."""
    pasta = settings.BPA_LOTES_DIR
    os.makedirs(pasta, exist_ok=True)
    pasta_norm = os.path.normpath(pasta)
    caminho = os.path.normpath(os.path.join(pasta_norm, nome_arquivo))
    if os.path.commonpath([pasta_norm, caminho]) != pasta_norm:
        raise BusinessRuleError("Nome de arquivo inválido.")
    return caminho


def listar_lotes() -> list[dict]:
    pasta = settings.BPA_LOTES_DIR
    if not os.path.isdir(pasta):
        return []
    arquivos = []
    for nome in os.listdir(pasta):
        if not nome.lower().endswith(".txt"):
            continue
        caminho = os.path.join(pasta, nome)
        stat = os.stat(caminho)
        arquivos.append({
            "nome": nome,
            "tamanho": stat.st_size,
            "modificado_em": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    arquivos.sort(key=lambda a: a["nome"], reverse=True)
    return arquivos


def ler_lote(nome_arquivo: str) -> str:
    caminho = _caminho_lote(nome_arquivo)
    if not os.path.exists(caminho):
        raise NotFoundError("Lote", nome_arquivo)
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def salvar_lote(nome_arquivo: str, conteudo: str) -> None:
    caminho = _caminho_lote(nome_arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)


def criar_cabecalho_lote(nome_arquivo: str, medico: str, data: str) -> None:
    """Adiciona um cabeçalho de bloco (cria o arquivo se não existir)."""
    caminho = _caminho_lote(nome_arquivo)
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")


def adicionar_documento_lote(nome_arquivo: str, documento: str) -> None:
    """
    Adiciona um CNS/CPF ao bloco atual. Se o bloco já tiver 99 documentos
    (limite por folha do BPA), duplica o último cabeçalho antes de
    adicionar — começa um novo bloco sem perder a referência do médico/data.
    """
    caminho = _caminho_lote(nome_arquivo)
    doc_limpo = re.sub(r"\D", "", documento).strip()
    if not doc_limpo:
        raise BusinessRuleError("Documento inválido.")

    pacientes_no_lote = 0
    ultimo_cabecalho = ""
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            linhas = f.readlines()
        for linha in reversed(linhas):
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue
            if linha_limpa.upper().startswith("PROFISSIONAL:"):
                ultimo_cabecalho = linha_limpa
                break
            pacientes_no_lote += 1

    with open(caminho, "a", encoding="utf-8") as f:
        if pacientes_no_lote >= 99 and ultimo_cabecalho:
            f.write(f"\n{ultimo_cabecalho}\n")
        f.write(f"{doc_limpo}\n")


# ── Análise e geração do arquivo BPA-I ───────────────────────────────────────
def _analisar_lote_sync(caminho: str) -> list[dict]:
    grupos = bpa.ler_arquivo_lote(caminho)
    con = bpa.conectar()
    try:
        profissionais = bpa.listar_profissionais(con)
        analise = []

        for idx, grupo in enumerate(grupos):
            item = {
                "indice": idx,
                "medico_raw": grupo["medico_raw"],
                "data": grupo["data"],
                "qtd_documentos": len(grupo["documentos"]),
                "profissional_status": "nao_encontrado",
                "cns_prof": None,
                "nome_prof": None,
                "categoria_status": None,
                "categoria": None,
                "candidatos_profissional": [],
                "categorias_possiveis": [],
            }

            resolucao = bpa.resolver_profissional_por_nome(profissionais, grupo["medico_raw"])
            item["profissional_status"] = resolucao["status"]

            if resolucao["status"] == "auto":
                cns_prof = resolucao["cns"]
                item["cns_prof"]  = cns_prof.zfill(15)
                item["nome_prof"] = resolucao["nome"].upper()

                categoria, automatico = bpa.detectar_categoria(con, cns_prof)
                if automatico:
                    item["categoria_status"] = "auto"
                    item["categoria"] = categoria
                elif categoria:
                    item["categoria_status"] = "ambiguo"
                    item["categorias_possiveis"] = categoria
                else:
                    item["categoria_status"] = "desconhecido"
                    item["categorias_possiveis"] = list(bpa.PROCEDIMENTOS.keys())
            else:
                item["candidatos_profissional"] = [
                    {"cns": cns.zfill(15), "nome": nome.upper()}
                    for cns, nome in resolucao["candidatos"]
                ]

            analise.append(item)

        return analise
    finally:
        con.close()


async def analisar_lote(nome_arquivo: str) -> dict:
    caminho = _caminho_lote(nome_arquivo)
    if not os.path.exists(caminho):
        raise NotFoundError("Lote", nome_arquivo)
    try:
        grupos = await run_in_threadpool(_analisar_lote_sync, caminho)
    except bpa.LoteError as e:
        raise BusinessRuleError(str(e))
    return {"arquivo": nome_arquivo, "grupos": grupos}


def _gerar_de_resolucoes_sync(caminho: str, resolucoes: list[dict]) -> dict:
    grupos = bpa.ler_arquivo_lote(caminho)
    resolucao_por_indice = {r["indice"]: r for r in resolucoes}

    con = bpa.conectar()
    try:
        todas_linhas: list[str] = []
        n_folhas_total = 0
        competencias: list[str] = []
        todos_nao_encontrados: list[str] = []

        for idx, grupo in enumerate(grupos):
            resolucao = resolucao_por_indice.get(idx)
            if not resolucao:
                continue

            try:
                data_dt = datetime.strptime(grupo["data"], "%d/%m/%Y")
            except ValueError:
                continue
            data_aten   = data_dt.strftime("%Y%m%d")
            competencia = data_aten[:6]

            cns_prof  = resolucao["cns_prof"].zfill(15)
            categoria = resolucao["categoria"]

            pacientes, nao_encontrados, _invalidos = bpa.buscar_pacientes(con, grupo["documentos"])
            todos_nao_encontrados.extend(nao_encontrados)
            if not pacientes:
                continue

            competencias.append(competencia)
            proc = bpa.PROCEDIMENTOS[categoria]["codigo"]
            cbo  = bpa.PROCEDIMENTOS[categoria]["cbo"]
            linhas, n_folhas = bpa.montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia)
            todas_linhas.extend(linhas)
            n_folhas_total += n_folhas

        if not todas_linhas:
            raise bpa.LoteError("Nenhuma linha gerada — confira as resoluções enviadas.")

        competencia_predominante = max(set(competencias), key=competencias.count)
        cabecalho = bpa.montar_cabecalho(
            competencia_predominante, len(todas_linhas), n_folhas_total, todas_linhas
        )
        ok, _tam = bpa.validar(todas_linhas)
        caminho_gerado = bpa.gerar_arquivo(todas_linhas, cabecalho, competencia_predominante)

        return {
            "arquivo_gerado": os.path.basename(caminho_gerado),
            "validacao_ok": ok,
            "registros": len(todas_linhas),
            "folhas": n_folhas_total,
            "competencia": competencia_predominante,
            "nao_encontrados": todos_nao_encontrados,
        }
    finally:
        con.close()


async def gerar_arquivo_de_lote(nome_arquivo: str, resolucoes: list[dict]) -> dict:
    caminho = _caminho_lote(nome_arquivo)
    if not os.path.exists(caminho):
        raise NotFoundError("Lote", nome_arquivo)
    try:
        return await run_in_threadpool(_gerar_de_resolucoes_sync, caminho, resolucoes)
    except bpa.LoteError as e:
        raise BusinessRuleError(str(e))


def caminho_arquivo_gerado(nome_arquivo: str) -> str:
    """Resolve o caminho do BPA-I já gerado em ~/Downloads, validando o nome."""
    if not re.fullmatch(r"BPAI_\d+_\d{6}\.txt", nome_arquivo):
        raise BusinessRuleError("Nome de arquivo inválido.")
    pasta = os.path.join(os.path.expanduser("~"), "Downloads")
    caminho = os.path.join(pasta, nome_arquivo)
    if not os.path.exists(caminho):
        raise NotFoundError("Arquivo gerado", nome_arquivo)
    return caminho
