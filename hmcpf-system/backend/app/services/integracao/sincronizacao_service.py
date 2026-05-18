from __future__ import annotations

import io
from logging import getLogger

from app.database import firebird as fb
from app.repositories import cadcns_repository as cadcns_repo
from app.services.integracao.utils import (
    apenas_numeros,
    remove_accents,
)

logger = getLogger(__name__)


def sincronizar_firebird() -> str:
    logger.info("sincronizar_firebird: iniciando padronizacao do CADCNS")
    saida = io.StringIO()
    saida.write("=== SINCRONIZAR FIREBIRD (Padronizar CADCNS) ===\n\n")

    if fb.firebirdsql is None:
        return "fb.firebirdsql nao instalado."

    if not fb.FB_PATH.exists():
        logger.error("sincronizar_firebird: BPAMAG.GDB nao encontrado em %s", fb.FB_PATH)
        return f"BPAMAG.GDB nao encontrado: {fb.FB_PATH}"

    try:
        con = fb.firebirdsql.connect(**fb.FB_CONNECT_ARGS)
    except Exception as e:
        logger.error("sincronizar_firebird: erro ao conectar: %s", e)
        return f"Erro ao conectar Firebird: {e}"

    saida.write("Lendo pacientes do BPAMAG.GDB...\n")
    try:
        pacientes = cadcns_repo.listar_pacientes(con)
    except Exception as e:
        con.close()
        return f"Erro ao consultar CADCNS: {e}"

    if not pacientes:
        con.close()
        return "Nenhum paciente encontrado no CADCNS."

    saida.write(f"Total de registros: {len(pacientes)}\n")
    saida.write("Padronizando dados (removendo acentos, ajustando telefones, sexo, enderecos)...\n\n")

    sucessos = 0
    erros = 0

    for p in pacientes:
        try:
            nome_original = p[0]
            dtnasc = p[1]
            if not nome_original or not dtnasc:
                continue

            nome_limpo = remove_accents(nome_original)[:30].strip()
            cpf = apenas_numeros(p[2])[:11] if p[2] else ""
            sus = apenas_numeros(p[3])[:15] if p[3] else ""
            sexo_raw = str(p[4]).strip().upper() if p[4] else ""
            sexo = sexo_raw[:1] if sexo_raw in ("M", "F") else "F"

            rua = remove_accents(p[5])[:25] if p[5] else "R. PRINCIPAL"
            numero = remove_accents(p[6])[:5] if p[6] else "S/N"
            bairro = remove_accents(p[7])[:15] if p[7] else "CENTRO"

            ddd_original = apenas_numeros(p[8]) if p[8] else ""
            tel_original = apenas_numeros(p[9]) if p[9] else ""
            tel_full = ddd_original + tel_original
            if len(tel_full) <= 9 and tel_full:
                tel_full = "84" + tel_full
            ddd = tel_full[:2] if len(tel_full) >= 10 else ""
            tel = tel_full[-8:] if len(tel_full) >= 8 else tel_full

            cadcns_repo.atualizar_paciente(
                con, nome_limpo, cpf, sus, sexo,
                rua, numero, bairro, ddd, tel,
                nome_original, dtnasc,
            )
            sucessos += 1

        except Exception:
            erros += 1

    con.commit()
    con.close()

    logger.info("sincronizar_firebird: %d padronizados, %d erros", sucessos, erros)
    saida.write(f"Registros padronizados: {sucessos}\n")
    saida.write(f"Erros: {erros}\n")

    return saida.getvalue()
