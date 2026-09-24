"""Produção no Firebird do BPA Magnético: conferência (digitado x S_PRD),
situação do dia e reenvio dos faltantes.

Escreve no Firebird (S_PRD) — a numeração de folha/sequência vem do
bpa_gerador."""
from datetime import datetime

import bpa_gerador as bpa
import conferencia


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


def situacao_dia(data_br: str) -> dict:
    """Digitados no lote do dia x já no BPA Magnético (S_PRD) -- a Conferência
    de um dia só, resumida pra aparecer na Digitação."""
    try:
        dia = datetime.strptime((data_br or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return {"ok": False, "erro": "Data inválida (use DD/MM/AAAA)."}
    try:
        r = conferencia.conferir_periodo(dia, dia)
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}
    if not r["dias"]:
        return {"ok": True, "data": data_br, "digitados": 0, "no_bpa": 0, "faltando": 0, "tem_lote": False}
    d = r["dias"][0]
    faltando = sum(len(p["faltando_no_banco"]) for p in d["profissionais"])
    return {"ok": True, "data": data_br, "digitados": d["total_digitado"], "no_bpa": d["total_banco"],
            "faltando": faltando, "tem_lote": True}
