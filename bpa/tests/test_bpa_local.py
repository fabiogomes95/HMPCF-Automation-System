"""Rotas novas do BPA local (usadas pela aba BPA do sistema) e a migração
automática do dia. Firebird e PostgreSQL simulados."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import bpa_gerador as bpa
from bpa_local.cache import cache
from bpa_local.services import migracao, migracao_auto


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setattr(bpa, "BPA_LOTES_DIR", str(tmp_path))
    monkeypatch.setattr(bpa, "carregar_pacientes_cadcns", lambda: [
        {"sus": "700000000000001", "nome": "MARIA DA SILVA", "dtnasc": "15/01/1990", "cpf": "12345678909"},
        {"sus": "", "nome": "JOSE SANTOS", "dtnasc": "01/02/1980", "cpf": "98765432100"},
    ])
    monkeypatch.setattr(bpa, "carregar_profissionais_cadmed", lambda: [
        {"cns": "111111111111111", "nome": "DR MEDICO", "categoria": "medico", "cbo": "225125"},
        {"cns": "222222222222222", "nome": "ENF A", "categoria": "enfermeiro", "cbo": "223505"},
    ])
    monkeypatch.setattr(migracao_auto, "ARQUIVO", tmp_path / "migracao_auto.json")
    monkeypatch.setattr(migracao_auto, "_estado", {"situacao": "nunca"})
    from bpa_local.main import app
    with TestClient(app) as c:
        yield c


def test_lote_com_nomes_e_categorias(cliente):
    Path(bpa.BPA_LOTES_DIR, "05-09-2026.txt").write_text(
        "PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 05/09/2026\n12345678909\n00000000191\n"
        "PROFISSIONAL: ENF A | CNS: 222222222222222 | DATA: 05/09/2026\n98765432100\n",
        encoding="utf-8",
    )
    r = cliente.get("/api/lote", params={"arquivo": "05-09-2026.txt"}).json()
    assert r["ok"]
    assert [b["categoria"] for b in r["blocos"]] == ["medico", "enfermeiro"]
    assert r["blocos"][0]["pacientes"] == [
        {"doc": "12345678909", "nome": "MARIA DA SILVA"},
        {"doc": "00000000191", "nome": ""},          # não está no Firebird: sem nome
    ]
    assert cliente.get("/api/lote", params={"arquivo": "01-01-2020.txt"}).json()["ok"] is False


def test_profissionais_e_status(cliente):
    assert [p["categoria"] for p in cliente.get("/api/profissionais").json()] == ["medico", "enfermeiro"]
    st = cliente.get("/api/status").json()
    assert st["ok"] and st["pacientes"] == 2 and st["migracao_auto"]["situacao"] == "nunca"


# ── Migração automática ──────────────────────────────────────────────────────
def _estado(**kw):
    migracao_auto._estado.clear()
    migracao_auto._estado.update(kw)


def test_precisa_rodar(cliente):
    agora = datetime(2026, 9, 24, 8, 0)
    _estado(situacao="nunca")
    assert migracao_auto.precisa_rodar(agora)
    _estado(situacao="ok", data="2026-09-24")
    assert not migracao_auto.precisa_rodar(agora)                 # já rodou hoje
    _estado(situacao="ok", data="2026-09-23")
    assert migracao_auto.precisa_rodar(agora)                     # virou o dia
    _estado(situacao="rodando", data="2026-09-24")
    assert not migracao_auto.precisa_rodar(agora)
    _estado(situacao="erro", data="2026-09-24", fim=(agora - timedelta(minutes=3)).isoformat())
    assert not migracao_auto.precisa_rodar(agora)                 # erro recente: espera
    _estado(situacao="erro", data="2026-09-24", fim=(agora - timedelta(minutes=30)).isoformat())
    assert migracao_auto.precisa_rodar(agora)


def test_rodar_grava_resultado(cliente, monkeypatch):
    consultas = []

    def falso_migrar(query):
        consultas.append(query)
        yield {"tipo": "log", "msg": "x", "total": 120}
        yield {"tipo": "progresso", "i": 50, "total": 120, "msg": ""}
        yield {"tipo": "fim", "inseridos": 7, "atualizados": 2, "duplicatas": 111, "erros": 0, "cpf_invalidos": 0}

    monkeypatch.setattr(migracao, "migrar", falso_migrar)
    _estado(situacao="rodando")
    migracao_auto._rodar()
    e = migracao_auto.estado()
    assert e["situacao"] == "ok" and e["inseridos"] == 7 and e["atualizados"] == 2 and e["total"] == 120
    assert "INNER JOIN recepcao_atendimentos" in consultas[0]
    assert migracao_auto.ARQUIVO.exists()                         # sobrevive a reinício do BPA
    assert not migracao.TRAVA.locked()


def test_rodar_com_erro(cliente, monkeypatch):
    monkeypatch.setattr(migracao, "migrar", lambda q: iter([{"tipo": "erro", "msg": "PostgreSQL indisponível: x"}]))
    _estado(situacao="rodando")
    migracao_auto._rodar()
    e = migracao_auto.estado()
    assert e["situacao"] == "erro" and "PostgreSQL" in e["erro"]


def test_manual_e_automatica_nunca_juntas(cliente, monkeypatch):
    monkeypatch.setenv("BPA_MIGRACAO_AUTO", "1")
    migracao.TRAVA.acquire()
    try:
        # automática não dispara enquanto a manual roda...
        assert migracao_auto.executar_se_preciso() is False
        # ...e a manual recusa se a automática estiver rodando
        eventos = list(migracao.stream("202609"))
        assert "migração em andamento" in eventos[0]
    finally:
        migracao.TRAVA.release()


def test_desfazer_so_o_ultimo(cliente):
    arq = Path(bpa.BPA_LOTES_DIR, "06-09-2026.txt")
    arq.write_text("PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 06/09/2026\n"
                   "12345678909\n98765432100\n", encoding="utf-8")
    # não é o último: recusa e não mexe no arquivo
    r = cliente.post("/api/desfazer", json={"arquivo": "06-09-2026.txt", "cpf": "12345678909"}).json()
    assert r["ok"] is False
    assert arq.read_text(encoding="utf-8").count("12345678909") == 1
    # o último sai
    assert cliente.post("/api/desfazer", json={"arquivo": "06-09-2026.txt", "cpf": "987.654.321-00"}).json() == {"ok": True}
    assert arq.read_text(encoding="utf-8").endswith("12345678909\n")
    # depois de um cabeçalho novo (outro médico), o último registro não é paciente: recusa
    cliente.post("/api/cabecalho", json={"medico": "OUTRO", "cns": "", "data": "06/09/2026"})
    r = cliente.post("/api/desfazer", json={"arquivo": "06-09-2026.txt", "cpf": "12345678909"}).json()
    assert r["ok"] is False and "12345678909" in arq.read_text(encoding="utf-8")


def test_gerar_com_arquivo_aberto_da_mensagem_clara(cliente, monkeypatch):
    # Simula o Windows recusando sobrescrever (arquivo aberto no BPA Magnético etc.)
    Path(bpa.BPA_LOTES_DIR, "07-09-2026.txt").write_text(
        "PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 07/09/2026\n12345678909\n", encoding="utf-8")

    class Con:
        def close(self): pass
    monkeypatch.setattr(bpa, "conectar", lambda: Con())
    monkeypatch.setattr(bpa, "detectar_categoria", lambda con, cns: ("medico", True))
    monkeypatch.setattr(bpa, "buscar_pacientes", lambda con, docs: ([{"cpf": d} for d in docs], [], []))
    monkeypatch.setattr(bpa, "contar_producao_real", lambda *a, **k: 0)
    monkeypatch.setattr(bpa, "montar_linhas", lambda *a: (["X" * 350], 1))
    monkeypatch.setattr(bpa, "montar_cabecalho", lambda *a: "C" * 130)
    import builtins
    abrir_original = builtins.open

    def abrir(caminho, modo="r", *a, **k):
        if "BPA_MEDICOS_" in str(caminho) and "w" in modo:
            raise PermissionError(13, "Permission denied")
        return abrir_original(caminho, modo, *a, **k)
    monkeypatch.setattr(builtins, "open", abrir)

    r = cliente.post("/api/gerar", json={"arquivo": "07-09-2026.txt", "categoria": "medico"}).json()
    assert r["ok"] is False
    assert "BPA_MEDICOS_07092026.txt" in r["erro"] and "aberto em outro programa" in r["erro"]


def test_gerar_arquivo_com_paciente_sem_documento(cliente, monkeypatch):
    """Ponta a ponta com a geração REAL (só o Firebird simulado): paciente com
    CPF sai com 'n'; paciente digitado pelo cadastro sem CPF/SUS sai em branco e com 's'."""
    Path(bpa.BPA_LOTES_DIR, "10-09-2026.txt").write_text(
        "PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 10/09/2026\n12345678909\nID:777\n", encoding="utf-8")
    cadcns = [
        ("", "TESTE COM CPF", "19900101", "F", "240360", "03", "", "010", "081", "59575000",
         "RUA A", "1", "", "CENTRO", "84", "999999999", "", "12345678909", 776),
        ("", "TESTE SEM DOCUMENTO", "19850505", "M", "240360", "03", "", "010", "081", "59575000",
         "RUA B", "2", "", "CENTRO", "84", "988888888", "", "", 777),
    ]

    class Cur:
        def execute(self, sql, params=None):
            self._r = cadcns if "FROM CADCNS" in sql else []

        def fetchall(self):
            return self._r

    class Con:
        def cursor(self): return Cur()
        def close(self): pass

    monkeypatch.setattr(bpa, "conectar", lambda: Con())
    monkeypatch.setattr(bpa, "detectar_categoria", lambda con, cns: ("medico", True))
    monkeypatch.setattr(bpa, "contar_producao_real", lambda *a, **k: 0)

    r = cliente.post("/api/gerar", json={"arquivo": "10-09-2026.txt", "categoria": "medico"}).json()
    assert r["ok"], r
    assert r["arquivos"]["medico"]["registros"] == 2
    linhas = Path(r["arquivos"]["medico"]["caminho"]).read_bytes().decode("latin-1").split("\r\n")
    com_cpf, sem_doc = linhas[1], linhas[2]
    assert com_cpf.endswith("12345678909nn")                   # CPF, rua "n", possui "n"
    assert sem_doc.endswith(" " * 11 + "ns")                    # CPF em branco, rua "n", sem documento "s"
    assert "TESTE SEM DOCUMENTO" in sem_doc
    # prd-cnspac: logo depois de ident(2)+cnes(7)+cmp(6)+cnsmed(15)+cbo(6)+dtaten(8)+flh(3)+seq(2)+pa(10)
    assert sem_doc[59:74] == " " * 15                           # sem CNS
