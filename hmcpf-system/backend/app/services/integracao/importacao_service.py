from __future__ import annotations

import csv
import io
import os
from logging import getLogger

from app.database.legacy import get_legacy_conn
from app.repositories import paciente_repository as paciente_repo
from app.services.integracao.utils import (
    apenas_numeros,
    dn_iso,
    format_telefone,
    gerar_linha_bpa,
    parse_endereco,
    remove_accents,
    salvar_buffer,
    valida_cns,
)

logger = getLogger(__name__)


def importar_csv(separador: str = ";", caminho_csv: str = "") -> str:
    logger.info("importar_csv: arquivo=%s, separador=%s", caminho_csv or "*", separador)
    saida = io.StringIO()
    saida.write("=== IMPORTAR CSV (SMART UPDATE) ===\n\n")

    if not caminho_csv:
        return "Erro: Informe o caminho do CSV."
    arquivos = [caminho_csv]

    try:
        conn = get_legacy_conn()
    except Exception as e:
        logger.error("importar_csv: erro ao conectar: %s", e)
        return f"Erro ao conectar hospital.db: {e}"

    novos = 0
    atualizados = 0
    intactos = 0
    ignorados = 0
    relatorio_novos: list[str] = []

    for arq in arquivos:
        saida.write(f"\nProcessando: {arq}\n")
        try:
            with open(arq, "r", encoding="utf-8") as f:
                linhas = list(csv.reader(f, delimiter=separador))
        except Exception:
            try:
                with open(arq, "r", encoding="latin1") as f:
                    linhas = list(csv.reader(f, delimiter=separador))
            except Exception as e:
                saida.write(f"  Erro ao ler: {e}\n")
                continue

        for i, linha in enumerate(linhas):
            if i == 0:
                continue
            if len(linha) < 2:
                continue
            nome = (linha[0] or "").strip().upper()
            dn = (linha[1] or "").strip() if len(linha) > 1 else ""
            sexo = (linha[2] or "").strip().upper() if len(linha) > 2 else ""
            cpf = apenas_numeros(linha[3]) if len(linha) > 3 else ""
            sus = apenas_numeros(linha[4]) if len(linha) > 4 else ""
            if not valida_cns(sus):
                ignorados += 1
                continue
            if not nome:
                ignorados += 1
                continue
            existing = paciente_repo.buscar_por_sus(conn, sus)
            if existing:
                updates: dict[str, str] = {}
                if not existing.get("cpf") and cpf:
                    updates["cpf"] = cpf
                if not existing.get("nome") and nome:
                    updates["nome"] = nome
                if not existing.get("dn") and dn:
                    updates["dn"] = dn
                if not existing.get("sexo") and sexo:
                    updates["sexo"] = sexo
                if updates:
                    paciente_repo.atualizar_por_sus(conn, sus, updates)
                    conn.commit()
                    atualizados += 1
                else:
                    intactos += 1
            else:
                try:
                    paciente_repo.inserir(conn, {"nome": nome, "dn": dn, "sexo": sexo, "cpf": cpf, "sus": sus})
                    novos += 1
                    relatorio_novos.append(f"{nome} | SUS: {sus} | CPF: {cpf}")
                except Exception as e:
                    saida.write(f"  Erro inserir linha {i}: {e}\n")

    conn.commit()
    conn.close()

    saida.write(f"\n=== RESUMO ===\n")
    logger.info("importar_csv: novos=%d atualizados=%d intactos=%d ignorados=%d", novos, atualizados, intactos, ignorados)
    saida.write(f"\n=== RESUMO ===\n")
    saida.write(f"Novos cadastros: {novos}\n")
    saida.write(f"Atualizados (parciais): {atualizados}\n")
    saida.write(f"Intactos (ja completos): {intactos}\n")
    saida.write(f"Ignorados (SUS invalido): {ignorados}\n")

    if relatorio_novos:
        nome_rel = "relatorio_importacao.txt"
        with open(nome_rel, "w", encoding="utf-8") as f:
            f.write("\n".join(relatorio_novos))
        saida.write(f"Relatorio: {os.path.abspath(nome_rel)}\n")

    return saida.getvalue()


def converter_csv(caminho_csv: str = "", caminho_salvar: str = "") -> str:
    logger.info("converter_csv: arquivo=%s, salvar=%s", caminho_csv or "*", caminho_salvar or "padrao")
    saida = io.StringIO()
    saida.write("=== CONVERTER CSV ANTIGO → TXT BPA ===\n\n")

    if not caminho_csv:
        return "Erro: Informe o caminho do CSV."

    try:
        with open(caminho_csv, "r", encoding="utf-8") as f:
            linhas = list(csv.reader(f, delimiter=";"))
    except Exception:
        try:
            with open(caminho_csv, "r", encoding="latin1") as f:
                linhas = list(csv.reader(f, delimiter=";"))
        except Exception as e:
            logger.error("converter_csv: erro ao ler CSV: %s", e)
            return f"Erro ao ler CSV: {e}"

    saida.write(f"Linhas lidas: {len(linhas)}\n\n")

    linhas_txt: list[str] = []
    erros: list[str] = []
    for i, linha in enumerate(linhas[1:], 2):
        if len(linha) < 13:
            erros.append(f"Linha {i}: colunas insuficientes ({len(linha)})")
            continue
        nome = remove_accents(linha[1])[:30].ljust(30)
        dn = dn_iso(linha[2])
        sexo = (linha[4] or "I")[0].upper()
        if sexo not in "MF":
            sexo = "I"
        sus = apenas_numeros(linha[9])
        if not valida_cns(sus):
            erros.append(f"Linha {i}: SUS invalido - {linha[9]}")
            continue
        endereco_raw = linha[11] if len(linha) > 11 else ""
        endereco, numero, bairro = parse_endereco(endereco_raw)
        ddd, fone = format_telefone(linha[12] if len(linha) > 12 else "")
        linhas_txt.append(gerar_linha_bpa(sus, nome, dn, sexo, endereco, numero, bairro, ddd, fone))

    nome_arquivo = caminho_salvar or "BPA_PLANILHA_ANTIGA.txt"
    caminho_salvo = salvar_buffer("".join(linhas_txt), nome_arquivo)

    saida.write(f"Registros convertidos: {len(linhas_txt)}\n")
    saida.write(f"Registros barrados: {len(erros)}\n")
    saida.write(f"Arquivo: {caminho_salvo}\n")

    if erros:
        nome_erro = nome_arquivo.replace(".txt", "_PACIENTES_SEM_CADASTRO.txt")
        path_erro = salvar_buffer("\n".join(erros), nome_erro, encoding="utf-8")
        logger.warning("converter_csv: %d erros (SUS invalido ou colunas insuficientes)", len(erros))
        saida.write(f"Erros: {path_erro}\n")

    logger.info("converter_csv: %d convertidos, %d erros", len(linhas_txt), len(erros))
    return saida.getvalue()


def gerar_conteudo_bpa(mes_ano: str = "") -> tuple[str, list[str], str]:
    try:
        conn = get_legacy_conn()
        rows = paciente_repo.listar_todos(conn, mes_ano)
        conn.close()
    except Exception as e:
        logger.error("gerar_conteudo_bpa: erro ao conectar: %s", e)
        raise

    linhas: list[str] = []
    erros: list[str] = []
    for row in rows:
        r = dict(row)
        sus = apenas_numeros(r.get("sus", ""))
        if len(sus) != 15 or not valida_cns(sus):
            erros.append(f"SUS invalido: {r.get('nome','')} - {sus or r.get('sus','')}")
            continue
        nome = remove_accents(r.get("nome", ""))[:30].ljust(30)
        dn = dn_iso(r.get("dn", ""))
        sexo = (r.get("sexo", "") or "I")[0].upper()
        if sexo not in "MF":
            sexo = "I"
        endereco, numero, bairro = parse_endereco(
            f"{r.get('endereco','')}, {r.get('numero','')} - {r.get('bairro','')}"
        )
        ddd, fone = format_telefone(r.get("tel", ""))
        linhas.append(gerar_linha_bpa(sus, nome, dn, sexo, endereco, numero, bairro, ddd, fone))

    return "".join(linhas), erros, f"{len(linhas)} exportados, {len(erros)} barrados"


def exportar_bpa(mes_ano: str = "", caminho_salvar: str = "") -> str:
    logger.info("exportar_bpa: mes_ano=%s, salvar=%s", mes_ano or "*", caminho_salvar or "padrao")
    saida = io.StringIO()
    saida.write("=== EXPORTAR SQLite → TXT BPA ===\n\n")

    try:
        conteudo, erros, resumo = gerar_conteudo_bpa(mes_ano)
    except Exception as e:
        logger.error("exportar_bpa: erro: %s", e)
        return f"Erro ao exportar: {e}"

    nome_arquivo = caminho_salvar or "BPA_EXPORTADO_SQLITE.txt"
    caminho_salvo = salvar_buffer(conteudo, nome_arquivo)

    saida.write(f"Registros exportados: {len(conteudo.splitlines())}\n")
    saida.write(f"Registros barrados: {len(erros)}\n")
    saida.write(f"Arquivo salvo: {caminho_salvo}\n")

    if erros:
        nome_erro = nome_arquivo.replace(".txt", "_ERROS.txt")
        path_erro = salvar_buffer("\n".join(erros), nome_erro, encoding="utf-8")
        logger.warning("exportar_bpa: %d registros barrados (SUS invalido)", len(erros))
        saida.write(f"Log de erros: {path_erro}\n")
        saida.write(f"\n--- PACIENTES BARRADOS ---\n")
        for e in erros[:20]:
            saida.write(f"  {e}\n")
        if len(erros) > 20:
            saida.write(f"  ... e mais {len(erros) - 20}\n")

    logger.info("exportar_bpa: %s", resumo)
    return saida.getvalue()
