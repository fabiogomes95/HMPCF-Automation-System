from __future__ import annotations

import io
from logging import getLogger

from app.database import firebird as fb
from app.repositories import cadcns_repository as cadcns_repo

logger = getLogger(__name__)


def corrigir_nulls(caminho_arquivo: str = "") -> str:
    logger.info("corrigir_nulls: iniciando")
    saida = io.StringIO()
    saida.write("=== CORRIGIR NULLS NO FIREBIRD ===\n\n")

    if fb.firebirdsql is None:
        return "fb.firebirdsql nao instalado."

    if not fb.FB_PATH.exists():
        logger.error("corrigir_nulls: BPAMAG.GDB nao encontrado")
        return f"BPAMAG.GDB nao encontrado: {fb.FB_PATH}"

    try:
        con = fb.firebirdsql.connect(**fb.FB_CONNECT_ARGS)
    except Exception as e:
        logger.error("corrigir_nulls: erro ao conectar: %s", e)
        return f"Erro ao conectar Firebird: {e}"

    saida.write("Lendo metadados das colunas do CADCNS...\n")
    try:
        updates = cadcns_repo.listar_metadados_colunas(con)
    except Exception as e:
        con.close()
        return f"Erro ao ler metadados: {e}"

    if not updates:
        con.close()
        return "Nenhuma coluna para corrigir."

    saida.write(f"Colunas a corrigir: {len(updates)}\n\n")
    total_texto = 0
    total_numero = 0

    for col, kind in updates:
        valor = "''" if kind == "texto" else "0"
        try:
            cadcns_repo.corrigir_null_coluna(con, col, kind)
            saida.write(f"  CADCNS.{col} -> {valor}\n")
            if kind == "texto":
                total_texto += 1
            else:
                total_numero += 1
        except Exception as e:
            saida.write(f"  Erro {col}: {e}\n")

    con.commit()
    con.close()

    logger.info("corrigir_nulls: %d texto + %d numerico = %d", total_texto, total_numero, total_texto + total_numero)
    saida.write(f"\nCampos texto zerados: {total_texto}\n")
    saida.write(f"Campos numericos zerados: {total_numero}\n")

    return saida.getvalue()


def limpar_duplicatas(caminho_arquivo: str = "") -> str:
    logger.info("limpar_duplicatas: iniciando")
    saida = io.StringIO()
    saida.write("=== LIMPAR DUPLICATAS NO FIREBIRD ===\n\n")

    if fb.firebirdsql is None:
        return "fb.firebirdsql nao instalado."

    if not fb.FB_PATH.exists():
        logger.error("limpar_duplicatas: BPAMAG.GDB nao encontrado")
        return f"BPAMAM.GDB nao encontrado: {fb.FB_PATH}"

    try:
        con = fb.firebirdsql.connect(**fb.FB_CONNECT_ARGS)
    except Exception as e:
        logger.error("limpar_duplicatas: erro ao conectar: %s", e)
        return f"Erro ao conectar Firebird: {e}"

    try:
        registros = cadcns_repo.listar_duplicatas(con)
    except Exception as e:
        con.close()
        return f"Erro ao consultar CADCNS: {e}"

    grupos: dict[str, list[dict]] = {}
    for reg in registros:
        grupos.setdefault(reg["cns"], []).append(reg)

    removidos = 0
    grupos_dup = 0

    for cns, lista in grupos.items():
        if len(lista) <= 1:
            continue
        grupos_dup += 1
        for ficha in lista:
            pts = 0
            if len(ficha["cpf"]) >= 11:
                pts += 5
            if ficha["endereco"]:
                pts += 1
            if ficha["tel"]:
                pts += 1
            ficha["pts"] = pts
        lista.sort(key=lambda x: x["pts"], reverse=True)
        for ficha in lista[1:]:
            try:
                cadcns_repo.deletar_por_db_key(con, ficha["db_key"])
                removidos += 1
            except Exception as e:
                saida.write(f"  Erro deletar {ficha['db_key']}: {e}\n")

    con.commit()
    con.close()

    logger.info("limpar_duplicatas: %d grupos, %d removidos", grupos_dup, removidos)
    saida.write(f"Grupos com duplicidade: {grupos_dup}\n")
    saida.write(f"Registros removidos: {removidos}\n")

    return saida.getvalue()
