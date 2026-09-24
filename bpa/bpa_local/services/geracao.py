"""Geração do arquivo BPA-I do dia (um arquivo por categoria), que é
importado à mão no BPA Magnético. Portado sem mudança do antigo app Flask —
a saída tem que continuar idêntica byte a byte (ver tests/test_paridade_api.py)."""
import os
from datetime import datetime

import bpa_gerador as bpa

ROTULO_ARQUIVO = {"medico": "MEDICOS", "enfermeiro": "ENFERMEIROS"}


def gerar(d: dict) -> dict:
    arquivo = (d.get("arquivo") or "").strip()
    # categoria: "medico" | "enfermeiro" | ausente/"" = gera os dois que existirem no lote
    categoria_filtro = (d.get("categoria") or "").strip() or None

    if not arquivo:
        return {"ok": False, "erro": "Escolha o lote (dia) para gerar."}

    caminho = bpa.caminho_lote(arquivo)
    try:
        grupos = bpa.ler_arquivo_lote(caminho)
    except bpa.LoteError as e:
        return {"ok": False, "erro": str(e)}

    # Todos os profissionais do lote do dia
    grupos = [g for g in grupos if g["documentos"]]
    if not grupos:
        return {"ok": False, "erro": "Nenhum paciente gravado. Registre pacientes antes de gerar."}

    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}

    try:
        # Linhas separadas por categoria — cada uma vira o SEU PRÓPRIO arquivo,
        # pra não depender de um único arquivo combinado (se um médico/enfermeiro
        # tiver algum problema no BPA, o outro continua intacto e importável).
        por_categoria: dict[str, dict] = {
            "medico": {"linhas": [], "n_folhas": 0, "competencias": []},
            "enfermeiro": {"linhas": [], "n_folhas": 0, "competencias": []},
        }
        nao_encontrados: list[str] = []

        dt_str = arquivo.replace(".txt", "").replace("-", "")  # "04-06-2026.txt" → "04062026"
        nomes_arquivo = {cat: f"BPA_{ROTULO_ARQUIVO[cat]}_{dt_str}.txt" for cat in por_categoria}

        for grupo in grupos:
            # ── CNS do profissional ──────────────────────────────────────────
            cns_raw = grupo.get("cns", "").strip()
            if cns_raw:
                cns_prof = cns_raw.zfill(15)
            else:
                profs_raw = bpa.listar_profissionais(con)
                res = bpa.resolver_profissional_por_nome(profs_raw, grupo["medico_raw"])
                if res["status"] != "auto":
                    return {"ok": False, "erro": f"Profissional '{grupo['medico_raw']}' não encontrado no Firebird."}
                cns_raw = res["cns"]
                cns_prof = cns_raw.zfill(15)

            # ── Categoria (médico/enfermeiro) ────────────────────────────────
            try:
                categoria, auto = bpa.detectar_categoria(con, cns_raw)
                if not auto or not categoria:
                    categoria = "medico"
            except Exception:
                categoria = "medico"

            # ── Data de atendimento ──────────────────────────────────────────
            try:
                dt = datetime.strptime(grupo["data"], "%d/%m/%Y")
                data_aten = dt.strftime("%Y%m%d")
                competencia = data_aten[:6]
            except (ValueError, KeyError):
                continue

            # ── Dados dos pacientes no Firebird ──────────────────────────────
            pacientes, nao_enc, _ = bpa.buscar_pacientes(con, grupo["documentos"])
            nao_encontrados.extend(nao_enc)
            if not pacientes:
                continue

            # ── Continua folha/sequência de onde a produção desse profissional
            # já está na competência (outros dias já gerados) — a folha do
            # BPA-I acumula por profissional ao longo do mês, não recomeça a
            # cada dia; completa a folha em aberto antes de abrir uma nova.
            proc = bpa.PROCEDIMENTOS[categoria]["codigo"]
            cbo = bpa.PROCEDIMENTOS[categoria]["cbo"]
            producao_anterior = bpa.contar_producao_real(con, cns_prof, competencia, excluir_data=data_aten)
            folha_inicial = producao_anterior // 99 + 1
            seq_inicial = producao_anterior % 99 + 1

            linhas, folha_final = bpa.montar_linhas(
                pacientes, proc, cbo, cns_prof, data_aten, competencia, folha_inicial, seq_inicial
            )
            alvo = por_categoria[categoria]
            alvo["linhas"].extend(linhas)
            alvo["n_folhas"] += folha_final - folha_inicial + 1
            alvo["competencias"].append(competencia)

        pasta = bpa.BPA_LOTES_DIR
        os.makedirs(pasta, exist_ok=True)

        arquivos_gerados: dict[str, dict] = {}
        for categoria, dados in por_categoria.items():
            if categoria_filtro and categoria != categoria_filtro:
                continue
            if not dados["linhas"]:
                continue
            competencia_final = max(set(dados["competencias"]), key=dados["competencias"].count)
            cabecalho = bpa.montar_cabecalho(
                competencia_final, len(dados["linhas"]), dados["n_folhas"], dados["linhas"]
            )

            nome_arquivo = nomes_arquivo[categoria]
            caminho_gerado = os.path.join(pasta, nome_arquivo)
            try:
                with open(caminho_gerado, "w", encoding="latin-1", newline="") as f:
                    f.write(cabecalho + "\r\n")
                    for linha in dados["linhas"]:
                        f.write(linha + "\r\n")
            except PermissionError:
                # Windows não deixa sobrescrever arquivo aberto em outro programa
                return {"ok": False, "erro": (
                    f"Não consegui salvar {nome_arquivo}: o arquivo está aberto em outro programa "
                    "(BPA Magnético, Bloco de Notas ou Excel) ou está marcado como somente leitura. "
                    "Feche-o e clique em gerar de novo."
                )}

            arquivos_gerados[categoria] = {
                "arquivo": nome_arquivo,
                "caminho": caminho_gerado,
                "registros": len(dados["linhas"]),
                "folhas": dados["n_folhas"],
                "competencia": f"{competencia_final[4:]}/{competencia_final[:4]}",
            }

        if not arquivos_gerados:
            detalhe = f" CPFs não encontrados: {', '.join(nao_encontrados)}" if nao_encontrados else ""
            rotulo = ROTULO_ARQUIVO.get(categoria_filtro, "").lower()
            alvo = f" de {rotulo}" if rotulo else ""
            return {"ok": False, "erro": f"Nenhum paciente{alvo} encontrado no Firebird.{detalhe}"}

        return {
            "ok": True,
            "arquivos": arquivos_gerados,  # {"medico": {...}, "enfermeiro": {...}}
            "nao_encontrados": nao_encontrados,
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}
    finally:
        con.close()
