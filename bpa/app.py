"""
BPA — Flask separado do dashboard Streamlit.

Porta padrão: 8503
Dois módulos:
  - Digitação: busca RAM do Firebird, grava CPF no lote.
  - Migração:  PostgreSQL (pacientes do mês com CPF) → Firebird CADCNS.
               Progresso em tempo real via Server-Sent Events (SSE).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import firebirdsql
import psycopg2
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

# ── Paths e .env ──────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent
DASHBOARD = BASE.parent / "dashboard"
BACKEND   = BASE.parent / "backend"

sys.path.insert(0, str(DASHBOARD))
# Ordem de carregamento (prioridade decrescente):
#   1. bpa/.env         — configuracoes locais da maquina (nao versionado)
#   2. dashboard/.env   — Firebird
#   3. backend/.env     — PostgreSQL
# Valores ja definidos nao sao sobrescritos pelas camadas seguintes.
load_dotenv(BASE      / ".env")                  # local — maquina especifica
load_dotenv(DASHBOARD / ".env", override=False)  # Firebird
load_dotenv(BACKEND   / ".env", override=False)  # PostgreSQL

import bpa_gerador as bpa

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Cache em RAM ──────────────────────────────────────────────────────────────
_pacientes:      list[dict] = []
_profissionais:  list[dict] = []
_erro_firebird:  str = ""


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

# ── Bootstrap local (legado/web_recepcao/assets) ──────────────────────────────
_LEGADO_ASSETS = BASE.parent / "legado" / "web_recepcao" / "assets"


@app.route("/assets/<path:nome>")
def assets(nome: str):
    return send_from_directory(_LEGADO_ASSETS, nome)


# ── Pagina principal ──────────────────────────────────────────────────────────
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
        return jsonify({"ok": False, "erro": "Preencha profissional e data completa."})
    arquivo = bpa.nome_arquivo_lote(data)
    bpa.criar_cabecalho_lote(arquivo, medico, data, cns=cns)
    return jsonify({"ok": True, "arquivo": arquivo})


@app.route("/api/gravar", methods=["POST"])
def api_gravar():
    d       = request.get_json(force=True)
    arquivo = (d.get("arquivo") or "").strip()
    cpf     = (d.get("cpf")     or "").strip()
    nome    = (d.get("nome")    or "").strip()
    if not arquivo or not cpf:
        return jsonify({"ok": False, "erro": "Arquivo ou CPF invalido."})
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


# ── Helpers de migração ───────────────────────────────────────────────────────
def _pg_connect():
    conn = psycopg2.connect(
        host    =os.getenv("POSTGRES_HOST",     "localhost"),
        port    =int(os.getenv("POSTGRES_PORT", "5432")),
        dbname  =os.getenv("POSTGRES_DB",       "hmpcf"),
        user    =os.getenv("POSTGRES_USER",     "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connect_timeout=5,
    )
    # Banco legado com dados em WIN1252 — sem isso psycopg2 tenta decodificar
    # bytes como UTF-8 e quebra nos caracteres especiais portugueses (ç, ã, ê…)
    conn.set_client_encoding("WIN1252")
    return conn


def _limpar(valor) -> str:
    if not valor:
        return ""
    return re.sub(r"\D", "", str(valor))


def _texto(valor, max_len=9999) -> str:
    if valor is None:
        return ""
    return str(valor).strip().upper()[:max_len]


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
    "ID_CADCNS", "CNS", "NUM_CPF", "NOME", "DTNASC", "SEXO", "RACA", "MAEPCN",
    "LOGPCN", "NUMPCN", "BAIRRO_PCNTE", "CEPPCN", "IBGE", "CO_LOGRAD",
    "ETNIA", "NACIONALIDADE", "DDTEL_PCNTE", "TEL_PCNTE",
]
_SQL_INSERT = (
    f"INSERT INTO CADCNS ({', '.join(_COLUNAS)}) "
    f"VALUES ({', '.join(['?']*len(_COLUNAS))})"
)


def _query_pacientes_mes(mes_aaaamm: str) -> str:
    """SQL que busca pacientes com CPF que tiveram atendimento no mes indicado."""
    ano = mes_aaaamm[:4]
    mes = mes_aaaamm[4:6]
    inicio = f"{ano}-{mes}-01"
    # primeiro dia do mes seguinte
    mes_i = int(mes)
    if mes_i == 12:
        fim = f"{int(ano)+1}-01-01"
    else:
        fim = f"{ano}-{mes_i+1:02d}-01"
    return f"""
        SELECT DISTINCT
            p.cns, p.num_cpf, p.nome, p.dtnasc, p.sexo, p.raca, p.maepcn,
            p.logpcn, p.numpcn, p.bairro_pcnte, p.ceppcn, p.ibge,
            p.nacionalidade, p.ddtel_pcnte, p.tel_pcnte
        FROM pacientes p
        INNER JOIN recepcao_atendimentos ra ON ra.paciente_id = p.id
        WHERE p.num_cpf IS NOT NULL AND p.num_cpf <> ''
          AND ra.data_atendimento >= '{inicio}'
          AND ra.data_atendimento <  '{fim}'
        ORDER BY p.nome
    """


# ── API — Migração: preview (contagem) ───────────────────────────────────────
@app.route("/api/migracao/preview", methods=["POST"])
def api_migracao_preview():
    mes = (request.get_json(force=True) or {}).get("mes", date.today().strftime("%Y%m"))
    try:
        pg = _pg_connect()
    except Exception as e:
        return jsonify({"ok": False, "erro": f"PostgreSQL: {e}"})
    try:
        cur = pg.cursor()
        # total de pacientes com CPF no mês
        sql = _query_pacientes_mes(mes)
        cur.execute(sql)
        rows = cur.fetchall()
        total = len(rows)

        # quantos já existem no Firebird
        fb = bpa.conectar()
        fb_cur = fb.cursor()
        ja_existem = sum(
            1 for r in rows
            if _paciente_existe_fb(fb_cur, _limpar(r[0]), _limpar(r[1]))
        )
        fb.close()
        return jsonify({
            "ok": True,
            "total": total,
            "novos": total - ja_existem,
            "ja_existem": ja_existem,
        })
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})
    finally:
        pg.close()


# ── API — Migração: execução com SSE ─────────────────────────────────────────
@app.route("/api/migracao/stream")
def api_migracao_stream():
    mes = request.args.get("mes", date.today().strftime("%Y%m"))

    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        # ── Conectar PostgreSQL ──────────────────────────────────────────────
        try:
            pg = _pg_connect()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"PostgreSQL indisponivel: {e}"})
            return

        yield _sse({"tipo": "log", "msg": "Conectado ao PostgreSQL."})

        # ── Buscar pacientes do mês ──────────────────────────────────────────
        try:
            pg_cur = pg.cursor()
            pg_cur.execute(_query_pacientes_mes(mes))
            rows = pg_cur.fetchall()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"Erro na consulta PostgreSQL: {e}"})
            pg.close()
            return

        total = len(rows)
        yield _sse({"tipo": "log", "msg": f"{total} paciente(s) com CPF encontrado(s) no mes.", "total": total})

        if total == 0:
            yield _sse({"tipo": "fim", "inseridos": 0, "duplicatas": 0, "erros": 0})
            pg.close()
            return

        # ── Conectar Firebird ────────────────────────────────────────────────
        try:
            fb = bpa.conectar()
            fb_cur = fb.cursor()
        except Exception as e:
            yield _sse({"tipo": "erro", "msg": f"Firebird indisponivel: {e}"})
            pg.close()
            return

        yield _sse({"tipo": "log", "msg": "Conectado ao Firebird."})

        # ── MAX ID ───────────────────────────────────────────────────────────
        fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
        max_id = fb_cur.fetchone()[0] or 0

        inseridos = 0
        duplicatas = 0
        erros = 0
        LOTE = 50

        for i, row in enumerate(rows, 1):
            cns_r, cpf_r, nome_r, dn_r, sexo_r, raca_r, mae_r, \
                log_r, num_r, bairro_r, cep_r, ibge_r, \
                nac_r, ddd_r, tel_r = row

            cns = _limpar(cns_r)
            cpf = _limpar(cpf_r)

            if _paciente_existe_fb(fb_cur, cns, cpf):
                duplicatas += 1
            else:
                max_id += 1
                valores = [
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
                    "081",
                    "",
                    _texto(nac_r, 3) or "010",
                    _texto(ddd_r, 2),
                    _texto(tel_r, 9),
                ]
                try:
                    fb_cur.execute(_SQL_INSERT, valores)
                    inseridos += 1
                except Exception as e:
                    erros += 1
                    yield _sse({"tipo": "log", "msg": f"Erro CPF {cpf}: {e}"})

            if i % LOTE == 0:
                fb.commit()
                yield _sse({
                    "tipo": "progresso",
                    "msg": f"{i}/{total} processados — inseridos: {inseridos} | duplicatas: {duplicatas}",
                    "i": i, "total": total,
                    "inseridos": inseridos, "duplicatas": duplicatas,
                })

        # ── Commit final + recarregar cache ──────────────────────────────────
        try:
            fb.commit()
        except Exception as e:
            yield _sse({"tipo": "log", "msg": f"Erro no commit final: {e}"})

        fb.close()
        pg.close()

        _carregar_pacientes()

        yield _sse({
            "tipo": "fim",
            "msg": f"Migracao concluida! Inseridos: {inseridos} | Duplicatas: {duplicatas} | Erros: {erros}",
            "inseridos": inseridos, "duplicatas": duplicatas, "erros": erros,
        })

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Inicialização ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("BPA_DIGITACAO_PORT", "8503"))
    print(f"\n  BPA Digitacao -> http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
