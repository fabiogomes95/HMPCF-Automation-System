"""Paridade entre o antigo app Flask (app.py) e o novo BPA local em FastAPI
(bpa_local): mesmas rotas, mesmas respostas e o MESMO arquivo BPA-I, byte a
byte. O Firebird é simulado — os dois apps chamam as mesmas funções do
bpa_gerador, então basta trocá-las uma vez.

Quando o app Flask sair (vai pro legado), este teste sai junto."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import bpa_gerador as bpa

SISTEMA = "http://192.168.1.29:8001"

PACIENTES_CACHE = [
    {"sus": "700000000000001", "nome": "MARIA DA SILVA", "dtnasc": "15/01/1990", "cpf": "12345678909"},
    {"sus": "700000000000002", "nome": "JOSE SANTOS", "dtnasc": "01/02/1980", "cpf": "98765432100"},
    {"sus": "", "nome": "ANA MARIA SOUZA", "dtnasc": "03/03/2000", "cpf": "11144477735"},
]
PROFISSIONAIS_CACHE = [
    {"cns": "111111111111111", "nome": "DR MEDICO", "categoria": "medico", "cbo": "225125"},
    {"cns": "222222222222222", "nome": "ENF ENFERMEIRA", "categoria": "enfermeiro", "cbo": "223505"},
]


def _pac(cpf: str, nome: str) -> dict:
    return {
        "cns": " " * 15, "nome": nome.ljust(30), "nasc": "19900115", "sexo": "F",
        "ibge": "240360", "raca": "03", "etnia": "    ", "nac": "010", "cep": "59575000",
        "lograd": "081", "end": "RUA TESTE".ljust(30), "compl": "".ljust(10),
        "num": "123".ljust(5), "bairro": "CENTRO".ljust(30), "ddd": "84",
        "tel": "999999999".ljust(9), "email": "".ljust(40), "cpf": cpf,
    }


class _FakeCon:
    def cursor(self):
        raise AssertionError("SQL direto não deveria rodar neste teste")

    def commit(self): pass
    def rollback(self): pass
    def close(self): pass


@pytest.fixture
def firebird_simulado(monkeypatch, tmp_path):
    monkeypatch.setattr(bpa, "BPA_LOTES_DIR", str(tmp_path))
    monkeypatch.setattr(bpa, "carregar_pacientes_cadcns", lambda: list(PACIENTES_CACHE))
    monkeypatch.setattr(bpa, "carregar_profissionais_cadmed", lambda: list(PROFISSIONAIS_CACHE))
    monkeypatch.setattr(bpa, "conectar", lambda: _FakeCon())
    monkeypatch.setattr(bpa, "listar_profissionais", lambda con: [("111111111111111", "DR MEDICO"),
                                                                  ("222222222222222", "ENF ENFERMEIRA")])
    monkeypatch.setattr(bpa, "detectar_categoria",
                        lambda con, cns: (("enfermeiro" if cns.lstrip("0").startswith("2") else "medico"), True))
    monkeypatch.setattr(bpa, "buscar_pacientes",
                        lambda con, docs: ([_pac(d, f"PACIENTE {d[-3:]}") for d in docs if d != "00000000191"],
                                           [d for d in docs if d == "00000000191"], []))
    # 150 atendimentos já no mês: a numeração tem que continuar na folha 2, seq 52
    monkeypatch.setattr(bpa, "contar_producao_real", lambda con, cns, comp, excluir_data=None: 150)
    return tmp_path


@pytest.fixture
def clientes(firebird_simulado):
    import app as app_flask  # antigo (carrega o cache na importação)
    app_flask._pacientes[:] = list(PACIENTES_CACHE)
    app_flask._profissionais[:] = list(PROFISSIONAIS_CACHE)
    from bpa_local.main import app as app_fastapi
    with TestClient(app_fastapi) as novo:
        yield app_flask.app.test_client(), novo


def _iguais(clientes, metodo, url, **kw):
    antigo, novo = clientes
    ra = getattr(antigo, metodo)(url, **kw)
    rn = getattr(novo, metodo)(url, **kw)
    assert ra.status_code == rn.status_code, url
    assert ra.get_json() == rn.json(), url
    return rn.json()


@pytest.mark.parametrize("url", [
    "/api/buscar?q=MARIA", "/api/buscar?q=MARIA&incluir_sus=0", "/api/buscar?q=7000&incluir_sus=1",
    "/api/buscar?q=M", "/api/prontuario/buscar?q=ab", "/api/fechamento?competencia=abc",
    "/api/conferencia?data_ini=99/99/9999&data_fim=01/01/2026",
])
def test_get_iguais(clientes, url):
    _iguais(clientes, "get", url)


@pytest.mark.parametrize("url,corpo", [
    ("/api/cabecalho", {"medico": "", "data": "01/09/2026"}),
    ("/api/gravar", {"arquivo": "", "cpf": ""}),
    ("/api/enfermeiros/dividir", {"data": "01/09"}),
    ("/api/enfermeiros/dividir", {"data": "01/09/2026", "enfermeiros": []}),
    ("/api/pacientes/completar", {"cns": "123", "cpf": "12345678909"}),
    ("/api/pacientes/completar", {"cns": "700000000000001", "cpf": "111"}),
    ("/api/conferencia/reenviar", {"data_ini": "x", "data_fim": "y"}),
    ("/api/gerar", {}),
    ("/api/gerar", {"arquivo": "01-01-2020.txt"}),
])
def test_post_validacoes_iguais(clientes, url, corpo):
    _iguais(clientes, "post", url, json=corpo)


def test_digitacao_e_lotes_iguais(clientes):
    antigo, novo = clientes
    for c in (antigo, novo):  # cada app grava no próprio dia
        dia = "02/09/2026" if c is antigo else "03/09/2026"
        cab = c.post("/api/cabecalho", json={"medico": "DR MEDICO", "cns": "111111111111111", "data": dia})
        corpo = cab.get_json() if c is antigo else cab.json()
        assert corpo["ok"] and corpo["existentes"] == 0
        g = c.post("/api/gravar", json={"arquivo": corpo["arquivo"], "cpf": "123.456.789-09", "nome": "MARIA"})
        assert (g.get_json() if c is antigo else g.json()) == {"ok": True, "nome": "MARIA"}
    a = Path(bpa.BPA_LOTES_DIR, "02-09-2026.txt").read_bytes()
    n = Path(bpa.BPA_LOTES_DIR, "03-09-2026.txt").read_bytes()
    assert a.replace(b"02/09/2026", b"03/09/2026") == n
    # Lista de lotes: mesmos arquivos, mesmo formato
    la, ln = antigo.get("/api/lotes").get_json(), novo.get("/api/lotes").json()
    assert [x["nome"] for x in la] == [x["nome"] for x in ln] == ["03-09-2026.txt", "02-09-2026.txt"]


def test_gerar_arquivo_bpa_identico_byte_a_byte(clientes):
    antigo, novo = clientes
    pasta = Path(bpa.BPA_LOTES_DIR)
    (pasta / "04-09-2026.txt").write_text(
        "PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 04/09/2026\n"
        "12345678909\n98765432100\n00000000191\n"
        "PROFISSIONAL: ENF ENFERMEIRA | CNS: 222222222222222 | DATA: 04/09/2026\n"
        "11144477735\n"
        "PROFISSIONAL: DR MEDICO | DATA: 04/09/2026\n"   # sem CNS: resolve pelo nome
        "52998224725\n",
        encoding="utf-8",
    )
    gerados = {}
    for nome, c in (("antigo", antigo), ("novo", novo)):
        r = c.post("/api/gerar", json={"arquivo": "04-09-2026.txt"})
        corpo = r.get_json() if nome == "antigo" else r.json()
        assert corpo["ok"], corpo
        gerados[nome] = (corpo, {cat: Path(info["caminho"]).read_bytes() for cat, info in corpo["arquivos"].items()})
        for info in corpo["arquivos"].values():
            Path(info["caminho"]).unlink()

    (json_a, arq_a), (json_n, arq_n) = gerados["antigo"], gerados["novo"]
    assert json_a == json_n
    assert set(arq_a) == {"medico", "enfermeiro"}
    for cat in arq_a:
        assert arq_a[cat] == arq_n[cat], f"arquivo {cat} diferente"
    assert json_n["arquivos"]["medico"]["registros"] == 3          # 2 + 1 resolvido pelo nome
    assert json_n["nao_encontrados"] == ["00000000191"]
    # continua a numeração do mês: 150 já lançados → folha 002, seq 52
    primeira = arq_n["medico"].split(b"\r\n")[1].decode("latin-1")
    assert primeira[44:49] == "00252"  # folha (3) + seq (2) logo após a data


def test_origem_e_preflight_iguais(clientes):
    antigo, novo = clientes
    estranho = {"Origin": "http://site-malicioso.com"}
    assert antigo.post("/api/gravar", json={}, headers=estranho).status_code == 403
    assert novo.post("/api/gravar", json={}, headers=estranho).status_code == 403
    pre = {"Origin": SISTEMA, "Access-Control-Request-Method": "POST",
           "Access-Control-Request-Private-Network": "true"}
    for r in (antigo.options("/api/gravar", headers=pre), novo.options("/api/gravar", headers=pre)):
        assert r.status_code == 204
        assert r.headers["Access-Control-Allow-Origin"] == SISTEMA
        assert r.headers["Access-Control-Allow-Private-Network"] == "true"
    # página local antiga (sem Origin / Origin local) continua funcionando
    assert novo.get("/api/lotes").status_code == 200
    assert novo.post("/api/gravar", json={}, headers={"Origin": "http://localhost:8503"}).status_code == 200


def test_status_novo(clientes):
    _, novo = clientes
    st = novo.get("/api/status").json()
    assert {k: st[k] for k in ("ok", "pacientes", "profissionais", "erro_firebird")} == {
        "ok": True, "pacientes": 3, "profissionais": 2, "erro_firebird": "",
    }
    assert "situacao" in st["migracao_auto"]
