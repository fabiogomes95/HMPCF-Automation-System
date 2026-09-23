"""Produção no Firebird do BPA Magnético: conferência (digitado x S_PRD),
reenvio dos faltantes, completar CPF de paciente e fechamento do mês.

Escreve no Firebird (S_PRD / CADCNS) — lógica portada sem mudança do antigo
app Flask; a numeração de folha/sequência vem do bpa_gerador."""
import re
from datetime import datetime

import bpa_gerador as bpa
import conferencia
import fechamento_mes

from bpa_local.cache import cache
from bpa_local.services import limpar


def _periodo(data_ini_str: str, data_fim_str: str):
    if data_ini_str and data_fim_str:
        return (
            datetime.strptime(data_ini_str, "%d/%m/%Y").date(),
            datetime.strptime(data_fim_str, "%d/%m/%Y").date(),
        )
    return conferencia.periodo_padrao()


def conferir(data_ini_str: str, data_fim_str: str) -> dict:
    try:
        data_ini, data_fim = _periodo(data_ini_str.strip(), data_fim_str.strip())
    except ValueError:
        return {"sucesso": False, "erro": "Datas inválidas (use DD/MM/AAAA)."}
    try:
        resultado = conferencia.conferir_periodo(data_ini, data_fim)
    except Exception as e:
        return {"sucesso": False, "erro": f"Firebird indisponível: {e}"}
    return {"sucesso": True, **resultado}


def completar_paciente(d: dict) -> dict:
    """Paciente sem CPF: completa o CPF na CADCNS e (opcional) já lança na produção."""
    cns = limpar(d.get("cns") or "")
    cpf = limpar(d.get("cpf") or "")
    data = (d.get("data") or "").strip()
    profissionais = d.get("profissionais") or []

    if len(cns) != 15:
        return {"ok": False, "erro": "CNS inválido."}
    if not bpa.valida_cpf(cpf):
        return {"ok": False, "erro": "CPF inválido."}
    if profissionais and len(data) < 10:
        return {"ok": False, "erro": "Informe a data (DD/MM/AAAA) para lançar na produção."}

    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}

    try:
        cur = con.cursor()
        cur.execute("SELECT NOME, NUM_CPF FROM CADCNS WHERE CNS = ?", (cns,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "erro": "Paciente não encontrado na CADCNS."}
        nome, cpf_atual = row
        cpf_atual = (cpf_atual or "").strip()
        if cpf_atual and cpf_atual != cpf:
            return {"ok": False, "erro": f"Paciente já tem outro CPF cadastrado ({cpf_atual})."}

        if cpf_atual != cpf:
            cur.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE CNS = ?", (cpf, cns))

        inseridos = []
        if profissionais:
            data_aten = datetime.strptime(data, "%d/%m/%Y").strftime("%Y%m%d")
            pacientes, _nao_encontrados, _invalidos = bpa.buscar_pacientes(con, [cns])
            if not pacientes:
                con.commit()
                return {
                    "ok": False,
                    "erro": "CPF gravado, mas não consegui recarregar os dados do paciente pra lançar na produção.",
                }
            pac = pacientes[0]

            for prof in profissionais:
                cns_prof = limpar(prof.get("cns") or "")
                nome_prof = (prof.get("nome") or "").strip()
                if not cns_prof:
                    continue
                categoria, auto = bpa.detectar_categoria(con, cns_prof)
                if not auto or not categoria:
                    inseridos.append({"profissional": nome_prof, "erro": "categoria não detectada automaticamente"})
                    continue
                registros = bpa.calcular_atendimentos_producao(con, cns_prof, categoria, data_aten, [pac])
                inseridos.append({
                    "profissional": nome_prof, "categoria": categoria,
                    "folha": registros[0]["folha"], "seq": registros[0]["seq"],
                })

        con.commit()
        cache.carregar_pacientes()
        return {"ok": True, "paciente": nome.strip(), "cpf": cpf, "inseridos": inseridos}
    except Exception as e:
        con.rollback()
        return {"ok": False, "erro": str(e)}
    finally:
        con.close()


def reenviar_faltantes(d: dict) -> dict:
    """Lança direto no S_PRD o que a conferência achou faltando (commit=False = só simula)."""
    data_ini_str = (d.get("data_ini") or "").strip()
    data_fim_str = (d.get("data_fim") or "").strip()
    commit = bool(d.get("commit"))

    try:
        data_ini, data_fim = _periodo(data_ini_str, data_fim_str)
    except ValueError:
        return {"ok": False, "erro": "Datas inválidas (use DD/MM/AAAA)."}

    try:
        resultado = conferencia.conferir_periodo(data_ini, data_fim)
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}

    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}

    dias_out = []
    total = 0
    try:
        for dia in resultado["dias"]:
            if dia["ok"]:
                continue
            data_aten = datetime.strptime(dia["data"], "%d/%m/%Y").strftime("%Y%m%d")
            profs_out = []
            for p in dia["profissionais"]:
                faltando = p["faltando_no_banco"]
                if not faltando:
                    continue
                cns_prof = p["cns"]
                if not cns_prof:
                    profs_out.append({"nome": p["nome"], "erro": "CNS do profissional não resolvido"})
                    continue
                categoria, auto = bpa.detectar_categoria(con, cns_prof)
                if not auto or not categoria:
                    profs_out.append({"nome": p["nome"], "cns": cns_prof, "erro": "categoria não detectada automaticamente"})
                    continue
                pacientes, nao_encontrados, _invalidos = bpa.buscar_pacientes(con, faltando)
                if not pacientes:
                    profs_out.append({
                        "nome": p["nome"], "cns": cns_prof,
                        "erro": "nenhum paciente encontrado na CADCNS",
                        "nao_encontrados": nao_encontrados,
                    })
                    continue

                registros = bpa.calcular_atendimentos_producao(
                    con, cns_prof, categoria, data_aten, pacientes, gravar=commit
                )
                total += len(registros)
                profs_out.append({
                    "nome": p["nome"], "cns": cns_prof, "categoria": categoria,
                    "qtd": len(registros),
                    "folha_ini": registros[0]["folha"], "seq_ini": registros[0]["seq"],
                    "folha_fim": registros[-1]["folha"], "seq_fim": registros[-1]["seq"],
                    "nao_encontrados": nao_encontrados,
                })
            if profs_out:
                dias_out.append({"data": dia["data"], "profissionais": profs_out})

        if commit:
            con.commit()

        return {
            "ok": True, "commit": commit, "total": total,
            "data_ini": resultado["data_ini"], "data_fim": resultado["data_fim"],
            "dias": dias_out,
        }
    except Exception as e:
        con.rollback()
        return {"ok": False, "erro": str(e)}
    finally:
        con.close()


def fechamento(competencia: str) -> dict:
    """4 checagens automáticas do mês, só leitura."""
    competencia = competencia.strip()
    if not re.fullmatch(r"\d{6}", competencia):
        return {"sucesso": False, "erro": "Competência inválida (esperado AAAAMM)."}
    try:
        return {"sucesso": True, **fechamento_mes.rodar(competencia)}
    except Exception as e:
        return {"sucesso": False, "erro": f"Firebird indisponível: {e}"}
