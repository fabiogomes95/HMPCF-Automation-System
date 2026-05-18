from __future__ import annotations

import csv
import io
import os
import re
from datetime import datetime
from logging import getLogger

from app.database.legacy import get_legacy_conn
from app.repositories import paciente_repository as paciente_repo
from app.services.integracao.utils import (
    apenas_numeros,
    parse_endereco,
    remove_accents,
    valida_cns,
)

logger = getLogger(__name__)

CABECALHOS = {"EXTREMOZ", "PACIENTE", "NOME", "REGISTRO"}


def sincronizar_contingencia(caminho_csv: str = "") -> str:
    logger.info("sincronizar_contingencia: arquivo=%s", caminho_csv or "*")
    saida = io.StringIO()
    saida.write("=== SINCRONIZAR CONTINGENCIA ===\n\n")

    if not caminho_csv:
        return "Erro: Informe o caminho do CSV de contingencia."

    if not os.path.exists(caminho_csv):
        logger.error("sincronizar_contingencia: arquivo nao encontrado: %s", caminho_csv)
        return f"Erro: Arquivo nao encontrado: {caminho_csv}"

    try:
        conn = get_legacy_conn()
    except Exception as e:
        logger.error("sincronizar_contingencia: erro ao conectar: %s", e)
        return f"Erro ao conectar hospital.db: {e}"

    pacientes = paciente_repo.listar_cpf_sus(conn)
    mapa_banco = {
        apenas_numeros(str(p["cpf"] or "")): (p, apenas_numeros(str(p["sus"] or "")))
        for p in pacientes
    }

    adicionados = 0
    atualizados = 0
    ignorados = 0
    processados_log: list[str] = []
    erros_log: list[str] = []

    with open(caminho_csv, "r", encoding="latin-1", errors="replace") as f:
        content = f.read(4096)
        separador = ";" if content.count(";") > content.count(",") else ","

    with open(caminho_csv, "r", encoding="latin-1", errors="replace") as f:
        reader = csv.reader(f, delimiter=separador)
        for i, row in enumerate(reader):
            linha_num = i + 1
            if len(row) < 5:
                continue

            nome_raw = next((
                c for c in row
                if len(c) > 5
                and not re.search(r"\d", c)
                and c.upper().strip() not in CABECALHOS
            ), "")
            if not nome_raw:
                continue

            cpf_plan = apenas_numeros(next((
                re.search(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", c).group(0)
                for c in row
                if re.search(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", c)
            ), ""))

            sus_plan = apenas_numeros(next((
                c for c in row
                if len(apenas_numeros(c)) == 15
                and apenas_numeros(c)[0] in "12789"
            ), ""))

            id_paciente = f"NOME: {nome_raw[:30].ljust(30)} | CPF: {cpf_plan.ljust(11)}"
            if not cpf_plan and not sus_plan:
                continue

            if cpf_plan in mapa_banco:
                cpf_orig_banco = str(mapa_banco[cpf_plan][0].get("cpf") or "")
                sus_banco_limpo = mapa_banco[cpf_plan][1]
                if len(sus_banco_limpo) < 15:
                    if valida_cns(sus_plan):
                        conn.execute(
                            "UPDATE pacientes SET sus = ? WHERE cpf = ?",
                            (sus_plan, cpf_orig_banco),
                        )
                        atualizados += 1
                        processados_log.append(
                            f"[ATUALIZADO] {id_paciente} | NOVO SUS: {sus_plan}"
                        )
                    else:
                        erros_log.append(
                            f"Linha {linha_num:04d} | {id_paciente} | MOTIVO: SUS Invalido ({sus_plan})"
                        )
                else:
                    ignorados += 1
                continue

            if not valida_cns(sus_plan):
                erros_log.append(
                    f"Linha {linha_num:04d} | {id_paciente} | MOTIVO: SUS Invalido para novo cadastro"
                )
                continue

            data_banco = ""
            for col in row:
                m = re.search(r"(\d{2})[^\d]*(\d{2})[^\d]*(\d{4}|\d{2})", col)
                if m and len(col) < 15:
                    dia, mes, ano = m.groups()
                    if len(ano) == 2:
                        ano = "20" + ano if int(ano) < 30 else "19" + ano
                    data_banco = f"{ano}-{mes}-{dia}"
                    break

            if not data_banco:
                erros_log.append(
                    f"Linha {linha_num:04d} | {id_paciente} | MOTIVO: Data de Nascimento nao encontrada"
                )
                continue

            rua, num, bairro = parse_endereco(row[-1] if len(row) > 5 else "")

            paciente_repo.inserir_ou_substituir(conn, {
                "cpf": cpf_plan, "sus": sus_plan,
                "nome": remove_accents(nome_raw), "dn": data_banco,
                "sexo": " ", "raca": "PARDA",
                "endereco": rua, "numero": num, "bairro": bairro,
            })
            adicionados += 1
            processados_log.append(f"[NOVO]       {id_paciente} | SUS: {sus_plan}")

    conn.commit()
    conn.close()

    pasta_csv = os.path.dirname(caminho_csv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    if processados_log:
        nome_proc = os.path.join(pasta_csv, f"PROCESSADOS_{timestamp}.txt")
        with open(nome_proc, "w", encoding="utf-8") as f:
            f.write("--- PACIENTES PROCESSADOS COM SUCESSO ---\n\n")
            f.write("\n".join(processados_log))
        saida.write(f"Log processados: {nome_proc}\n")

    if erros_log:
        nome_err = os.path.join(pasta_csv, f"ERROS_SINCRONIZACAO_{timestamp}.txt")
        with open(nome_err, "w", encoding="utf-8") as f:
            f.write("--- PACIENTES COM ERRO ---\n\n")
            f.write("\n".join(erros_log))
        saida.write(f"Log erros: {nome_err}\n")

    logger.info("sincronizar_contingencia: novos=%d atualizados=%d ignorados=%d erros=%d",
                adicionados, atualizados, ignorados, len(erros_log))
    saida.write(f"\nNovos: {adicionados}\nAtualizados: {atualizados}\nJa OK: {ignorados}\n")
    if erros_log:
        saida.write(f"Atencao: {len(erros_log)} erros encontrados.\n")

    return saida.getvalue()
