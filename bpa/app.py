"""
BPA Digitação — app Flask separado, independente do dashboard Streamlit.

Carrega toda a CADCNS do Firebird na RAM na inicialização.
Busca é feita no Python via RAM (< 5 ms), retorna JSON pro JS.
Salva APENAS o CPF no lote — nunca o SUS.

Porta padrão: 8503
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

# ── Caminho para bpa_gerador e .env do dashboard ─────────────────────────────
BASE      = Path(__file__).resolve().parent
DASHBOARD = BASE.parent / "dashboard"
sys.path.insert(0, str(DASHBOARD))

from dotenv import load_dotenv
load_dotenv(DASHBOARD / ".env")

import bpa_gerador as bpa

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Cache de pacientes em RAM ─────────────────────────────────────────────────
_pacientes: list[dict] = []
_erro_firebird: str = ""


def _carregar_pacientes() -> None:
    global _pacientes, _erro_firebird
    try:
        _pacientes = bpa.carregar_pacientes_cadcns()
        _erro_firebird = ""
        print(f"[BPA] {len(_pacientes)} pacientes carregados do Firebird.")
    except Exception as e:
        _erro_firebird = str(e)
        print(f"[BPA] ERRO ao carregar Firebird: {e}")


_carregar_pacientes()


# ── Servir Bootstrap local (sem CDN) ─────────────────────────────────────────
_LEGADO_ASSETS = BASE.parent / "legado" / "web_recepcao" / "assets"


@app.route("/assets/<path:nome>")
def assets(nome: str):
    return send_from_directory(_LEGADO_ASSETS, nome)


# ── Páginas ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template(
        "index.html",
        total=len(_pacientes),
        erro_firebird=_erro_firebird,
    )


# ── API ───────────────────────────────────────────────────────────────────────
@app.route("/api/buscar")
def api_buscar():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    resultados = bpa.buscar_pacientes_memoria(q, _pacientes, limite=40)
    return jsonify(resultados)


@app.route("/api/cabecalho", methods=["POST"])
def api_cabecalho():
    d = request.get_json(force=True)
    medico = (d.get("medico") or "").strip()
    data   = (d.get("data")   or "").strip()
    if not medico or len(data) < 10:
        return jsonify({"ok": False, "erro": "Preencha médico e data completa."})
    arquivo = bpa.nome_arquivo_lote(data)
    bpa.criar_cabecalho_lote(arquivo, medico, data)
    return jsonify({"ok": True, "arquivo": arquivo})


@app.route("/api/gravar", methods=["POST"])
def api_gravar():
    d      = request.get_json(force=True)
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
    return jsonify({"ok": True, "total": len(_pacientes), "erro": _erro_firebird})


if __name__ == "__main__":
    port = int(os.getenv("BPA_DIGITACAO_PORT", "8503"))
    print(f"\n  BPA Digitacao -> http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
