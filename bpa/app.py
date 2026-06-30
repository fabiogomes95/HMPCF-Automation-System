"""
BPA — Flask unificado: digitação, geração do BPA-I e migração.

Porta padrão: 8503
O Streamlit (8502) não tem mais nada de BPA — só dashboard gerencial.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

# ── Paths e .env ──────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent
DASHBOARD = BASE.parent / "dashboard"
BACKEND   = BASE.parent / "backend"

sys.path.insert(0, str(DASHBOARD))

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

import bpa_gerador as bpa

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
    return render_template(
        "index.html",
        total=len(_pacientes),
        erro_firebird=_erro_firebird,
        profissionais_json=json.dumps(_profissionais, ensure_ascii=False),
        mes_atual=date.today().strftime("%Y%m"),
        mes_label=_nome_mes(date.today().month, date.today().year),
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


# ── API — Geração BPA-I ───────────────────────────────────────────────────────
@app.route("/api/gerar", methods=["POST"])
def api_gerar():
    d       = request.get_json(force=True) or {}
    arquivo = (d.get("arquivo") or "").strip()

    if not arquivo:
        return jsonify({"ok": False, "erro": "Nenhum arquivo ativo. Confirme o profissional e a data primeiro."})

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
        todas_linhas:    list[str] = []
        n_folhas_total   = 0
        competencias:    list[str] = []
        nao_encontrados: list[str] = []

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

            proc = bpa.PROCEDIMENTOS[categoria]["codigo"]
            cbo  = bpa.PROCEDIMENTOS[categoria]["cbo"]
            linhas, n_folhas = bpa.montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia)
            todas_linhas.extend(linhas)
            n_folhas_total += n_folhas
            competencias.append(competencia)

        if not todas_linhas:
            detalhe = f" CPFs não encontrados: {', '.join(nao_encontrados)}" if nao_encontrados else ""
            return jsonify({"ok": False, "erro": f"Nenhum paciente encontrado no Firebird.{detalhe}"})

        competencia_final = max(set(competencias), key=competencias.count)
        cabecalho = bpa.montar_cabecalho(competencia_final, len(todas_linhas), n_folhas_total, todas_linhas)

        # Um arquivo por dia: BPA_01062026.txt
        dt_str = arquivo.replace(".txt", "").replace("-", "")  # "01-06-2026.txt" → "01062026"
        nome_arquivo   = f"BPA_{dt_str}.txt"
        pasta          = bpa.BPA_LOTES_DIR
        os.makedirs(pasta, exist_ok=True)
        caminho_gerado = os.path.join(pasta, nome_arquivo)

        with open(caminho_gerado, "w", encoding="latin-1", newline="") as f:
            f.write(cabecalho + "\r\n")
            for linha in todas_linhas:
                f.write(linha + "\r\n")

        return jsonify({
            "ok":              True,
            "arquivo":         nome_arquivo,
            "caminho":         caminho_gerado,
            "registros":       len(todas_linhas),
            "folhas":          n_folhas_total,
            "competencia":     f"{competencia_final[4:]}/{competencia_final[:4]}",
            "nao_encontrados": nao_encontrados,
        })

    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})
    finally:
        con.close()


# ── Helpers migração ──────────────────────────────────────────────────────────
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


def _paciente_existe_fb(cur, cns: str, cpf: str) -> bool:
    if cns:
        cur.execute("SELECT 1 FROM CADCNS WHERE CNS = ?", (cns,))
        if cur.fetchone():
            return True
    if cpf:
        cur.execute("SELECT 1 FROM CADCNS WHERE NUM_CPF = ?", (cpf,))
        if cur.fetchone():
            return True
    return False


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
        fb = bpa.conectar()
        fb_cur = fb.cursor()
        ja_existem = sum(1 for r in rows if _paciente_existe_fb(fb_cur, _limpar(r[0]), _limpar(r[1])))
        fb.close()
        return jsonify({"ok": True, "total": total, "novos": total - ja_existem, "ja_existem": ja_existem})
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
            yield _sse({"tipo": "fim", "inseridos": 0, "duplicatas": 0, "erros": 0}); pg.close(); return

        try:
            fb = bpa.conectar()
            fb_cur = fb.cursor()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"Firebird indisponível: {e}"}); pg.close(); return

        yield _sse({"tipo": "log", "msg": "Conectado ao Firebird."})

        fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
        max_id = fb_cur.fetchone()[0] or 0

        inseridos = duplicatas = erros = 0
        LOTE = 50

        for i, row in enumerate(rows, 1):
            cns_r, cpf_r, nome_r, dn_r, sexo_r, raca_r, mae_r, \
                log_r, num_r, bairro_r, cep_r, ibge_r, nac_r, ddd_r, tel_r = row
            cns = _limpar(cns_r)
            cpf = _limpar(cpf_r)

            if _paciente_existe_fb(fb_cur, cns, cpf):
                duplicatas += 1
            else:
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
                except Exception as e:
                    erros += 1
                    yield _sse({"tipo": "log", "msg": f"Erro CPF {cpf}: {e}"})

            if i % LOTE == 0:
                fb.commit()
                yield _sse({
                    "tipo": "progresso",
                    "msg":  f"{i}/{total} — inseridos: {inseridos} | duplicatas: {duplicatas}",
                    "i": i, "total": total,
                    "inseridos": inseridos, "duplicatas": duplicatas,
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
            "msg":        f"Concluído! Inseridos: {inseridos} | Duplicatas: {duplicatas} | Erros: {erros}",
            "inseridos":  inseridos, "duplicatas": duplicatas, "erros": erros,
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
