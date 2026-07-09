"""
BPA — Flask unificado: digitação, geração do BPA-I e migração.

Porta padrão: 8503
O Streamlit (8502) não tem mais nada de BPA — só dashboard gerencial.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

# ── Paths e .env ──────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent
DASHBOARD = BASE.parent / "dashboard"
BACKEND   = BASE.parent / "backend"

# Ordem de prioridade (decrescente):
#   1. bpa/.env        — ajustes locais da máquina (não versionado)
#   2. dashboard/.env  — credenciais Firebird
#   3. backend/.env    — credenciais PostgreSQL
load_dotenv(BASE      / ".env")
load_dotenv(DASHBOARD / ".env", override=False)
load_dotenv(BACKEND   / ".env", override=False)

# Lotes ficam em bpa/bpa_lotes/ por padrão (sem precisar de .env)
if not os.getenv("BPA_LOTES_DIR"):
    os.environ["BPA_LOTES_DIR"] = str(BASE / "bpa_lotes")

import bpa_gerador as bpa  # agora vive em bpa/, mesmo diretorio deste arquivo
import conferencia

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Cache RAM ─────────────────────────────────────────────────────────────────
_pacientes:     list[dict] = []
_profissionais: list[dict] = []
_erro_firebird: str = ""


def _carregar_pacientes() -> None:
    global _pacientes, _erro_firebird
    try:
        _pacientes = bpa.carregar_pacientes_cadcns()
        _erro_firebird = ""
        print(f"[BPA] {len(_pacientes)} pacientes carregados do Firebird.")
    except Exception as e:
        _erro_firebird = str(e)
        print(f"[BPA] ERRO ao carregar pacientes: {e}")


def _carregar_profissionais() -> None:
    global _profissionais
    try:
        _profissionais = bpa.carregar_profissionais_cadmed()
        print(f"[BPA] {len(_profissionais)} profissionais carregados do Firebird.")
    except Exception as e:
        print(f"[BPA] ERRO ao carregar profissionais: {e}")


_carregar_pacientes()
_carregar_profissionais()

# ── Assets Bootstrap (offline) ────────────────────────────────────────────────
_ASSETS = BASE.parent / "legado" / "web_recepcao" / "assets"


@app.route("/assets/<path:nome>")
def assets(nome: str):
    return send_from_directory(_ASSETS, nome)


# ── Página principal ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    competencias = _competencias_disponiveis()
    if not competencias:
        competencias = [{
            "value": date.today().strftime("%Y%m"),
            "label": _nome_mes(date.today().month, date.today().year),
        }]
    return render_template(
        "index.html",
        total=len(_pacientes),
        erro_firebird=_erro_firebird,
        profissionais_json=json.dumps(_profissionais, ensure_ascii=False),
        competencias=competencias,
        mes_atual=competencias[0]["value"],
    )


def _nome_mes(m: int, a: int) -> str:
    nomes = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    return f"{nomes[m]}/{a}"


# ── API — Digitação ───────────────────────────────────────────────────────────
@app.route("/api/buscar")
def api_buscar():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    return jsonify(bpa.buscar_pacientes_memoria(q, _pacientes, limite=40))


@app.route("/api/cabecalho", methods=["POST"])
def api_cabecalho():
    d      = request.get_json(force=True)
    medico = (d.get("medico") or "").strip()
    cns    = (d.get("cns")    or "").strip()
    data   = (d.get("data")   or "").strip()
    if not medico or len(data) < 10:
        return jsonify({"ok": False, "erro": "Preencha profissional e data."})
    arquivo = bpa.nome_arquivo_lote(data)
    bpa.criar_cabecalho_lote(arquivo, medico, data, cns=cns)
    # contar pacientes já gravados no arquivo (sessões anteriores do dia)
    try:
        grupos = bpa.ler_arquivo_lote(bpa.caminho_lote(arquivo))
        existentes = sum(len(g["documentos"]) for g in grupos)
    except Exception:
        existentes = 0
    return jsonify({"ok": True, "arquivo": arquivo, "existentes": existentes})


@app.route("/api/gravar", methods=["POST"])
def api_gravar():
    d       = request.get_json(force=True)
    arquivo = (d.get("arquivo") or "").strip()
    cpf     = (d.get("cpf")     or "").strip()
    nome    = (d.get("nome")    or "").strip()
    if not arquivo or not cpf:
        return jsonify({"ok": False, "erro": "Arquivo ou CPF inválido."})
    try:
        bpa.adicionar_documento_lote(arquivo, cpf)
        return jsonify({"ok": True, "nome": nome})
    except bpa.LoteError as e:
        return jsonify({"ok": False, "erro": str(e)})


@app.route("/api/recarregar", methods=["POST"])
def api_recarregar():
    _carregar_pacientes()
    _carregar_profissionais()
    return jsonify({
        "ok":    True,
        "total": len(_pacientes),
        "erro":  _erro_firebird,
        "profs": _profissionais,
    })


# ── API — Buscar Prontuário (localizar dia/profissional nos lotes já digitados) ─
@app.route("/api/prontuario/buscar")
def api_prontuario_buscar():
    q = request.args.get("q", "").strip()
    if len(q) < 3:
        return jsonify({"ok": True, "pacientes": []})

    try:
        con = bpa.conectar()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Firebird indisponível: {e}"})
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
    return jsonify({"ok": True, "pacientes": pacientes})


# ── API — Enfermeiros (divide o CPF já digitado pros médicos entre enfermeiros) ─
@app.route("/api/enfermeiros/dividir", methods=["POST"])
def api_enfermeiros_dividir():
    d           = request.get_json(force=True) or {}
    data        = (d.get("data") or "").strip()
    enfermeiros = d.get("enfermeiros") or []

    if len(data) < 10:
        return jsonify({"ok": False, "erro": "Informe a data (DD/MM/AAAA)."})
    if not enfermeiros:
        return jsonify({"ok": False, "erro": "Selecione ao menos um enfermeiro."})

    arquivo = bpa.nome_arquivo_lote(data)
    caminho = bpa.caminho_lote(arquivo)
    try:
        grupos = bpa.ler_arquivo_lote(caminho)
    except bpa.LoteError as e:
        return jsonify({"ok": False, "erro": str(e)})

    try:
        con = bpa.conectar()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Firebird indisponível: {e}"})

    try:
        # Descarta qualquer divisão de enfermeiros já feita antes nesse dia
        # (refazer não deve duplicar) e junta só os CPFs vindos de médico.
        grupos_medico: list[dict] = []
        documentos: list[str] = []
        for g in grupos:
            cns_raw   = (g.get("cns") or "").strip()
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
            return jsonify({"ok": False, "erro": "Nenhum CPF de médico digitado nesse dia ainda."})

        distribuicao = bpa.dividir_por_profissionais(documentos, enfermeiros)

        novos_grupos = []
        resumo       = []
        for enf in enfermeiros:
            docs_enf = distribuicao.get(enf["cns"], [])
            if not docs_enf:
                continue
            novos_grupos.append({
                "medico_raw": enf["nome"], "cns": enf["cns"], "data": data, "documentos": docs_enf,
            })
            resumo.append({"nome": enf["nome"], "cns": enf["cns"], "qtd": len(docs_enf)})

        bpa.regravar_lote(arquivo, grupos_medico + novos_grupos)

        return jsonify({
            "ok": True, "arquivo": arquivo, "total": len(documentos), "distribuicao": resumo,
        })
    finally:
        con.close()


# ── API — Lotes disponíveis (para escolher o dia da geração) ──────────────────
@app.route("/api/lotes")
def api_lotes():
    return jsonify([
        {
            "nome": l["nome"],
            "tamanho": l["tamanho"],
            "modificado_em": l["modificado_em"].strftime("%d/%m/%Y %H:%M"),
        }
        for l in bpa.listar_lotes()
    ])


# ── API — Conferência (digitado x lote de produção no Firebird) ───────────────
@app.route("/api/conferencia")
def api_conferencia():
    data_ini_str = request.args.get("data_ini", "").strip()
    data_fim_str = request.args.get("data_fim", "").strip()
    try:
        if data_ini_str and data_fim_str:
            data_ini = datetime.strptime(data_ini_str, "%d/%m/%Y").date()
            data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y").date()
        else:
            data_ini, data_fim = conferencia.periodo_padrao()
    except ValueError:
        return jsonify({"sucesso": False, "erro": "Datas inválidas (use DD/MM/AAAA)."})

    try:
        resultado = conferencia.conferir_periodo(data_ini, data_fim)
    except Exception as e:
        return jsonify({"sucesso": False, "erro": f"Firebird indisponível: {e}"})

    return jsonify({"sucesso": True, **resultado})


# ── API — Paciente sem CPF: completa o CPF e (opcional) já lança na produção ──
@app.route("/api/pacientes/completar", methods=["POST"])
def api_pacientes_completar():
    d             = request.get_json(force=True) or {}
    cns           = _limpar(d.get("cns") or "")
    cpf           = _limpar(d.get("cpf") or "")
    data          = (d.get("data") or "").strip()
    profissionais = d.get("profissionais") or []

    if len(cns) != 15:
        return jsonify({"ok": False, "erro": "CNS inválido."})
    if not bpa.valida_cpf(cpf):
        return jsonify({"ok": False, "erro": "CPF inválido."})
    if profissionais and len(data) < 10:
        return jsonify({"ok": False, "erro": "Informe a data (DD/MM/AAAA) para lançar na produção."})

    try:
        con = bpa.conectar()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Firebird indisponível: {e}"})

    try:
        cur = con.cursor()
        cur.execute("SELECT NOME, NUM_CPF FROM CADCNS WHERE CNS = ?", (cns,))
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "erro": "Paciente não encontrado na CADCNS."})
        nome, cpf_atual = row
        cpf_atual = (cpf_atual or "").strip()
        if cpf_atual and cpf_atual != cpf:
            return jsonify({"ok": False, "erro": f"Paciente já tem outro CPF cadastrado ({cpf_atual})."})

        if cpf_atual != cpf:
            cur.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE CNS = ?", (cpf, cns))

        inseridos = []
        if profissionais:
            data_aten = datetime.strptime(data, "%d/%m/%Y").strftime("%Y%m%d")
            pacientes, _nao_encontrados, _invalidos = bpa.buscar_pacientes(con, [cns])
            if not pacientes:
                con.commit()
                return jsonify({
                    "ok": False,
                    "erro": "CPF gravado, mas não consegui recarregar os dados do paciente pra lançar na produção.",
                })
            pac = pacientes[0]

            for prof in profissionais:
                cns_prof  = _limpar(prof.get("cns") or "")
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
        _carregar_pacientes()
        return jsonify({"ok": True, "paciente": nome.strip(), "cpf": cpf, "inseridos": inseridos})
    except Exception as e:
        con.rollback()
        return jsonify({"ok": False, "erro": str(e)})
    finally:
        con.close()


# ── API — Reenviar faltantes da conferência direto pra produção (S_PRD) ───────
@app.route("/api/conferencia/reenviar", methods=["POST"])
def api_conferencia_reenviar():
    d            = request.get_json(force=True) or {}
    data_ini_str = (d.get("data_ini") or "").strip()
    data_fim_str = (d.get("data_fim") or "").strip()
    commit       = bool(d.get("commit"))

    try:
        if data_ini_str and data_fim_str:
            data_ini = datetime.strptime(data_ini_str, "%d/%m/%Y").date()
            data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y").date()
        else:
            data_ini, data_fim = conferencia.periodo_padrao()
    except ValueError:
        return jsonify({"ok": False, "erro": "Datas inválidas (use DD/MM/AAAA)."})

    try:
        resultado = conferencia.conferir_periodo(data_ini, data_fim)
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Firebird indisponível: {e}"})

    try:
        con = bpa.conectar()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Firebird indisponível: {e}"})

    dias_out = []
    total    = 0
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

        return jsonify({
            "ok": True, "commit": commit, "total": total,
            "data_ini": resultado["data_ini"], "data_fim": resultado["data_fim"],
            "dias": dias_out,
        })
    except Exception as e:
        con.rollback()
        return jsonify({"ok": False, "erro": str(e)})
    finally:
        con.close()


# ── API — Geração BPA-I ───────────────────────────────────────────────────────
_ROTULO_ARQUIVO = {"medico": "MEDICOS", "enfermeiro": "ENFERMEIROS"}


@app.route("/api/gerar", methods=["POST"])
def api_gerar():
    d        = request.get_json(force=True) or {}
    arquivo  = (d.get("arquivo") or "").strip()
    # categoria: "medico" | "enfermeiro" | ausente/"" = gera os dois que existirem no lote
    categoria_filtro = (d.get("categoria") or "").strip() or None

    if not arquivo:
        return jsonify({"ok": False, "erro": "Escolha o lote (dia) para gerar."})

    caminho = bpa.caminho_lote(arquivo)
    try:
        grupos = bpa.ler_arquivo_lote(caminho)
    except bpa.LoteError as e:
        return jsonify({"ok": False, "erro": str(e)})

    # Todos os profissionais do lote do dia
    grupos = [g for g in grupos if g["documentos"]]

    if not grupos:
        return jsonify({"ok": False, "erro": "Nenhum paciente gravado. Registre pacientes antes de gerar."})

    try:
        con = bpa.conectar()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Firebird indisponível: {e}"})

    try:
        # Linhas separadas por categoria — cada uma vira o SEU PRÓPRIO arquivo,
        # pra não depender de um único arquivo combinado (se um médico/enfermeiro
        # tiver algum problema no BPA, o outro continua intacto e importável).
        por_categoria: dict[str, dict] = {
            "medico":     {"linhas": [], "n_folhas": 0, "competencias": []},
            "enfermeiro": {"linhas": [], "n_folhas": 0, "competencias": []},
        }
        nao_encontrados: list[str] = []

        dt_str        = arquivo.replace(".txt", "").replace("-", "")  # "04-06-2026.txt" → "04062026"
        nomes_arquivo = {cat: f"BPA_{_ROTULO_ARQUIVO[cat]}_{dt_str}.txt" for cat in por_categoria}

        for grupo in grupos:
            # ── CNS do profissional ──────────────────────────────────────────
            cns_raw = grupo.get("cns", "").strip()
            if cns_raw:
                cns_prof = cns_raw.zfill(15)
            else:
                profs_raw = bpa.listar_profissionais(con)
                res = bpa.resolver_profissional_por_nome(profs_raw, grupo["medico_raw"])
                if res["status"] != "auto":
                    return jsonify({"ok": False,
                                    "erro": f"Profissional '{grupo['medico_raw']}' não encontrado no Firebird."})
                cns_raw  = res["cns"]
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
                dt          = datetime.strptime(grupo["data"], "%d/%m/%Y")
                data_aten   = dt.strftime("%Y%m%d")
                competencia = data_aten[:6]
            except (ValueError, KeyError):
                continue

            # ── Buscar dados dos pacientes no Firebird ───────────────────────
            pacientes, nao_enc, _ = bpa.buscar_pacientes(con, grupo["documentos"])
            nao_encontrados.extend(nao_enc)
            if not pacientes:
                continue

            # ── Continuar folha/sequência de onde a produção desse profissional
            # já está na competência (outros dias já gerados) — a folha do
            # BPA-I acumula por profissional ao longo do mês, não recomeça a
            # cada dia; completa a folha em aberto antes de abrir uma nova.
            proc = bpa.PROCEDIMENTOS[categoria]["codigo"]
            cbo  = bpa.PROCEDIMENTOS[categoria]["cbo"]
            producao_anterior = bpa.contar_producao_real(
                con, cns_prof, competencia, excluir_data=data_aten
            )
            folha_inicial = producao_anterior // 99 + 1
            seq_inicial   = producao_anterior % 99 + 1

            linhas, folha_final = bpa.montar_linhas(
                pacientes, proc, cbo, cns_prof, data_aten, competencia, folha_inicial, seq_inicial
            )
            alvo = por_categoria[categoria]
            alvo["linhas"].extend(linhas)
            alvo["n_folhas"] += folha_final - folha_inicial + 1
            alvo["competencias"].append(competencia)

        pasta  = bpa.BPA_LOTES_DIR
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

            nome_arquivo   = nomes_arquivo[categoria]
            caminho_gerado = os.path.join(pasta, nome_arquivo)
            with open(caminho_gerado, "w", encoding="latin-1", newline="") as f:
                f.write(cabecalho + "\r\n")
                for linha in dados["linhas"]:
                    f.write(linha + "\r\n")

            arquivos_gerados[categoria] = {
                "arquivo":     nome_arquivo,
                "caminho":     caminho_gerado,
                "registros":   len(dados["linhas"]),
                "folhas":      dados["n_folhas"],
                "competencia": f"{competencia_final[4:]}/{competencia_final[:4]}",
            }

        if not arquivos_gerados:
            detalhe = f" CPFs não encontrados: {', '.join(nao_encontrados)}" if nao_encontrados else ""
            rotulo  = _ROTULO_ARQUIVO.get(categoria_filtro, "").lower()
            alvo    = f" de {rotulo}" if rotulo else ""
            return jsonify({"ok": False, "erro": f"Nenhum paciente{alvo} encontrado no Firebird.{detalhe}"})

        return jsonify({
            "ok":              True,
            "arquivos":        arquivos_gerados,   # {"medico": {...}, "enfermeiro": {...}}
            "nao_encontrados": nao_encontrados,
        })

    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})
    finally:
        con.close()


# ── Helpers migração ──────────────────────────────────────────────────────────
def _competencias_disponiveis() -> list[dict]:
    """Meses (YYYYMM) que realmente têm atendimento no Postgres, mais recente primeiro."""
    try:
        pg = _pg_connect()
    except Exception:
        return []
    try:
        cur = pg.cursor()
        cur.execute("""
            SELECT DISTINCT to_char(data_atendimento, 'YYYYMM') AS ym
            FROM recepcao_atendimentos
            ORDER BY ym DESC
        """)
        return [
            {"value": ym, "label": _nome_mes(int(ym[4:6]), int(ym[:4]))}
            for (ym,) in cur.fetchall()
        ]
    except Exception:
        return []
    finally:
        pg.close()


def _pg_connect():
    conn = psycopg2.connect(
        host    =os.getenv("POSTGRES_HOST",     "localhost"),
        port    =int(os.getenv("POSTGRES_PORT", "5432")),
        dbname  =os.getenv("POSTGRES_DB",       "hmpcf"),
        user    =os.getenv("POSTGRES_USER",     "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connect_timeout=5,
        options ="-c client_encoding=LATIN1",
    )
    return conn


def _limpar(valor) -> str:
    return re.sub(r"\D", "", str(valor)) if valor else ""


def _texto(valor, max_len=9999) -> str:
    return str(valor).strip().upper()[:max_len] if valor is not None else ""


def _sexo(valor) -> str:
    s = _texto(valor, 1)
    return s if s in ("M", "F") else "I"


def _dtnasc(valor) -> str | None:
    if not valor:
        return None
    v = re.sub(r"\D", "", str(valor))
    return v if len(v) == 8 else None


def _cpf_valido(cpf: str) -> bool:
    return bpa.valida_cpf(cpf)


def _cns_valido(cns: str) -> bool:
    return len(cns) == 15


def _carregar_existentes_fb(cur) -> tuple[dict, set]:
    """Carrega todos os CNS/CPF já cadastrados no Firebird de uma vez (1 consulta),
    para checar existência em memória em vez de 1 SELECT por paciente (CADCNS não
    tem índice em NUM_CPF — em memória evita a varredura completa da tabela repetida
    milhares de vezes, sem precisar mexer no schema do banco).

    Retorna (por_cns, cpf_set):
      por_cns  — {CNS: (ID_CADCNS, NUM_CPF atual)}, para achar cadastros antigos
                 (só CNS, sem CPF) e completar o CPF sem duplicar o registro.
      cpf_set  — conjunto de CPFs já gravados em algum registro.
    """
    cur.execute("SELECT ID_CADCNS, CNS, NUM_CPF FROM CADCNS")
    por_cns: dict = {}
    cpf_set: set = set()
    for id_cadcns, cns, cpf in cur.fetchall():
        cns = (cns or "").strip()
        cpf = (cpf or "").strip()
        if cns:
            por_cns[cns] = (id_cadcns, cpf)
        if cpf:
            cpf_set.add(cpf)
    return por_cns, cpf_set


def _status_paciente(por_cns: dict, cpf_set: set, cns: str, cpf: str):
    """Decide o que fazer com um paciente do Postgres:
      "duplicata" — CPF já gravado em algum registro, nada a fazer.
      "atualizar" — já existe cadastro pelo CNS, mas sem CPF; (status, ID_CADCNS).
      "novo"      — não existe cadastro nenhum; precisa inserir.
    """
    if cpf in cpf_set:
        return ("duplicata", None)
    if cns and cns in por_cns:
        id_existente, cpf_atual = por_cns[cns]
        if not cpf_atual:
            return ("atualizar", id_existente)
        return ("duplicata", None)
    return ("novo", None)


_COLUNAS = [
    "ID_CADCNS","CNS","NUM_CPF","NOME","DTNASC","SEXO","RACA","MAEPCN",
    "LOGPCN","NUMPCN","BAIRRO_PCNTE","CEPPCN","IBGE","CO_LOGRAD",
    "ETNIA","NACIONALIDADE","DDTEL_PCNTE","TEL_PCNTE",
]
_SQL_INSERT = (
    f"INSERT INTO CADCNS ({', '.join(_COLUNAS)}) "
    f"VALUES ({', '.join(['?']*len(_COLUNAS))})"
)


def _query_pacientes_mes(mes_aaaamm: str) -> str:
    if not re.fullmatch(r"\d{6}", mes_aaaamm or ""):
        raise ValueError(f"Parametro 'mes' invalido: {mes_aaaamm!r} (esperado AAAAMM)")
    ano, mes = mes_aaaamm[:4], mes_aaaamm[4:6]
    inicio   = f"{ano}-{mes}-01"
    mes_i    = int(mes)
    fim      = f"{int(ano)+1}-01-01" if mes_i == 12 else f"{ano}-{mes_i+1:02d}-01"
    return f"""
        SELECT DISTINCT p.cns, p.num_cpf, p.nome, p.dtnasc, p.sexo, p.raca, p.maepcn,
            p.logpcn, p.numpcn, p.bairro_pcnte, p.ceppcn, p.ibge,
            p.nacionalidade, p.ddtel_pcnte, p.tel_pcnte
        FROM pacientes p
        INNER JOIN recepcao_atendimentos ra ON ra.paciente_id = p.id
        WHERE p.num_cpf IS NOT NULL AND p.num_cpf <> ''
          AND ra.data_atendimento >= '{inicio}'
          AND ra.data_atendimento <  '{fim}'
        ORDER BY p.nome
    """


# ── API — Migração preview ────────────────────────────────────────────────────
@app.route("/api/migracao/preview", methods=["POST"])
def api_migracao_preview():
    mes = (request.get_json(force=True) or {}).get("mes", date.today().strftime("%Y%m"))
    try:
        pg = _pg_connect()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"PostgreSQL: {e}"})
    try:
        cur = pg.cursor()
        cur.execute(_query_pacientes_mes(mes))
        rows = cur.fetchall()
        total = len(rows)

        validos      = [r for r in rows if _cpf_valido(_limpar(r[1]))]
        cpf_invalido = total - len(validos)

        fb = bpa.conectar()
        fb_cur = fb.cursor()
        por_cns, cpf_set = _carregar_existentes_fb(fb_cur)
        fb.close()

        novos = atualizar = ja_existem = 0
        for r in validos:
            status, _ = _status_paciente(por_cns, cpf_set, _limpar(r[0]), _limpar(r[1]))
            if status == "novo":
                novos += 1
            elif status == "atualizar":
                atualizar += 1
            else:
                ja_existem += 1

        return jsonify({
            "ok": True, "total": total, "novos": novos, "atualizar": atualizar,
            "ja_existem": ja_existem, "cpf_invalido": cpf_invalido,
        })
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})
    finally:
        pg.close()


# ── API — Migração SSE ────────────────────────────────────────────────────────
@app.route("/api/migracao/stream")
def api_migracao_stream():
    mes = request.args.get("mes", date.today().strftime("%Y%m"))

    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        try:
            pg = _pg_connect()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"PostgreSQL indisponível: {e}"}); return

        yield _sse({"tipo": "log", "msg": "Conectado ao PostgreSQL."})

        try:
            cur = pg.cursor()
            cur.execute(_query_pacientes_mes(mes))
            rows = cur.fetchall()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"Consulta falhou: {e}"}); pg.close(); return

        total = len(rows)
        yield _sse({"tipo": "log", "msg": f"{total} paciente(s) com CPF no mês.", "total": total})

        if total == 0:
            yield _sse({
                "tipo": "fim", "inseridos": 0, "atualizados": 0, "duplicatas": 0,
                "erros": 0, "cpf_invalidos": 0,
            }); pg.close(); return

        try:
            fb = bpa.conectar()
            fb_cur = fb.cursor()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"Firebird indisponível: {e}"}); pg.close(); return

        yield _sse({"tipo": "log", "msg": "Conectado ao Firebird."})

        fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
        max_id = fb_cur.fetchone()[0] or 0

        por_cns, cpf_set = _carregar_existentes_fb(fb_cur)
        yield _sse({"tipo": "log", "msg": f"{len(cpf_set)} CPF(s) já cadastrados carregados em memória."})

        inseridos = atualizados = duplicatas = erros = cpf_invalidos = 0
        LOTE = 50

        for i, row in enumerate(rows, 1):
            cns_r, cpf_r, nome_r, dn_r, sexo_r, raca_r, mae_r, \
                log_r, num_r, bairro_r, cep_r, ibge_r, nac_r, ddd_r, tel_r = row
            cns = _limpar(cns_r)
            cpf = _limpar(cpf_r)

            if not _cpf_valido(cpf):
                cpf_invalidos += 1
                yield _sse({"tipo": "log", "msg": f"CPF ausente/inválido, paciente pulado: {nome_r} ({cpf_r!r})"})
                continue

            if cns and not _cns_valido(cns):
                cns = ""  # CNS não é mais obrigatório — descarta se mal formatado, mas mantém o CPF

            status, id_existente = _status_paciente(por_cns, cpf_set, cns, cpf)

            if status == "duplicata":
                duplicatas += 1

            elif status == "atualizar":
                try:
                    fb_cur.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE ID_CADCNS = ?", [cpf, id_existente])
                    atualizados += 1
                    cpf_set.add(cpf)
                    por_cns[cns] = (id_existente, cpf)
                except Exception as e:
                    erros += 1
                    yield _sse({"tipo": "log", "msg": f"Erro ao atualizar CPF de {nome_r} (CNS {cns}): {e}"})

            else:  # "novo"
                max_id += 1
                try:
                    fb_cur.execute(_SQL_INSERT, [
                        max_id, cns, cpf,
                        _texto(nome_r, 30) or "SEM NOME",
                        _dtnasc(dn_r),
                        _sexo(sexo_r),
                        _texto(raca_r, 2) or "03",
                        _texto(mae_r, 30),
                        _texto(log_r, 30) or "PRINCIPAL",
                        _texto(num_r, 5)  or "S/N",
                        _texto(bairro_r, 30) or "CENTRO",
                        _limpar(cep_r)[:8] or "59575000",
                        _limpar(ibge_r)[:6] or "240360",
                        "081", "",
                        _texto(nac_r, 3) or "010",
                        _texto(ddd_r, 2),
                        _texto(tel_r, 9),
                    ])
                    inseridos += 1
                    # Atualiza o cache em memória — sem isso, dois registros do mesmo
                    # paciente no mesmo lote (ex: endereço mudou entre atendimentos)
                    # seriam inseridos duas vezes no Firebird.
                    if cns:
                        por_cns[cns] = (max_id, cpf)
                    cpf_set.add(cpf)
                except Exception as e:
                    erros += 1
                    yield _sse({"tipo": "log", "msg": f"Erro CPF {cpf}: {e}"})

            if i % LOTE == 0:
                fb.commit()
                yield _sse({
                    "tipo": "progresso",
                    "msg":  f"{i}/{total} — inseridos: {inseridos} | atualizados: {atualizados} | duplicatas: {duplicatas}",
                    "i": i, "total": total,
                    "inseridos": inseridos, "atualizados": atualizados, "duplicatas": duplicatas,
                })

        try:
            fb.commit()
        except Exception as e:
            yield _sse({"tipo": "log", "msg": f"Erro no commit: {e}"})

        fb.close()
        pg.close()
        _carregar_pacientes()

        yield _sse({
            "tipo":       "fim",
            "msg":        f"Concluído! Inseridos: {inseridos} | Atualizados (CPF): {atualizados} | "
                          f"Duplicatas: {duplicatas} | CPF inválido: {cpf_invalidos} | Erros: {erros}",
            "inseridos":  inseridos, "atualizados": atualizados, "duplicatas": duplicatas, "erros": erros,
            "cpf_invalidos": cpf_invalidos,
        })

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("BPA_DIGITACAO_PORT", "8503"))
    print(f"\n  BPA -> http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
