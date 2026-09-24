"""Modo de teste (BPA_POSTGRES_FALSO): pacientes falsos no lugar do PostgreSQL,
e a migração inteira rodando contra eles com um Firebird simulado."""
import json
from datetime import date
from pathlib import Path

import bpa_gerador as bpa
from bpa_local import postgres
from bpa_local.postgres_falso import ConexaoFalsa
from bpa_local.services import migracao

JSON = Path(__file__).resolve().parent.parent / "teste" / "pacientes_falsos.json"
PACIENTES = json.loads(JSON.read_text(encoding="utf-8"))["pacientes"]


def test_arquivo_de_teste_so_tem_pacientes_teste():
    assert PACIENTES and all(p["nome"].startswith("TESTE ") for p in PACIENTES)


def test_competencias_e_filtro_por_periodo():
    cur = ConexaoFalsa(JSON).cursor()
    cur.execute("SELECT DISTINCT to_char(data_atendimento, 'YYYYMM') AS ym FROM recepcao_atendimentos")
    meses = [m for (m,) in cur.fetchall()]
    assert meses == sorted(meses, reverse=True) and len(meses) >= 2

    mes = meses[0]
    cur.execute(postgres.query_pacientes_mes(mes))
    linhas = cur.fetchall()
    esperados = {p["num_cpf"] for p in PACIENTES if any(a.replace("-", "")[:6] == mes for a in p["atendimentos"])}
    assert {l[1] or "" for l in linhas} == esperados  # inclui os sem CPF (vazio)
    assert len(linhas[0]) == 15  # mesmas colunas da consulta real


class _FbFalso:
    """Firebird em memória: 1 paciente que já tem CPF, 1 só com CNS e 1 sem
    documento (mesmo nome + nascimento de um paciente sem CPF do arquivo)."""

    def __init__(self, ja_tem_cpf: str, so_cns: str, sem_doc: dict):
        self.cadcns = [(1, "", ja_tem_cpf, "FULANO", "19900101"), (2, so_cns, "", "CICLANO", "19800101"),
                       (3, "", "", sem_doc["nome"][:30], sem_doc["dtnasc"])]
        self.inseridos, self.atualizados = [], []

    def cursor(self):
        fb = self

        class C:
            def execute(self, sql, params=None):
                if sql.startswith("SELECT MAX"):
                    self._r = [(max(linha[0] for linha in fb.cadcns),)]
                elif sql.startswith("SELECT ID_CADCNS"):
                    self._r = list(fb.cadcns)
                elif sql.startswith("INSERT"):
                    fb.inseridos.append(params)
                elif sql.startswith("UPDATE"):
                    fb.atualizados.append(params)

            def fetchone(self):
                return self._r[0]

            def fetchall(self):
                return self._r
        return C()

    def commit(self): pass
    def close(self): pass


def test_migracao_inteira_com_pacientes_falsos(monkeypatch):
    monkeypatch.setattr(postgres, "POSTGRES_FALSO", JSON)
    monkeypatch.setattr(bpa, "carregar_pacientes_cadcns", lambda: [])
    validos = [p for p in PACIENTES if bpa.valida_cpf(p["num_cpf"])]
    sem_doc = [p for p in PACIENTES if not p["num_cpf"]]
    assert len(sem_doc) == 6
    ja_tem = validos[5]
    so_cns = next(p for p in validos[6:] if p["cns"])
    fb = _FbFalso(ja_tem["num_cpf"], so_cns["cns"], sem_doc[0])
    monkeypatch.setattr(bpa, "conectar", lambda: fb)

    hoje = date.today()
    eventos = list(migracao.migrar(postgres.query_pacientes_periodo(date(2000, 1, 1), hoje.replace(year=hoje.year + 1))))
    fim = eventos[-1]
    assert fim["tipo"] == "fim"

    assert fim["cpf_invalidos"] == 2                     # os 2 CPFs inválidos de propósito
    assert fim["duplicatas"] == 2                        # 1 com CPF + 1 sem documento já no Firebird
    assert fim["atualizados"] == 1 and fb.atualizados[0][0] == so_cns["num_cpf"]  # completou CPF pelo SUS
    assert fim["sem_documento"] == len(sem_doc) - 1      # sem CPF: entram (menos o que já existia)
    assert fim["inseridos"] == (len(validos) - 2) + (len(sem_doc) - 1)
    assert all(linha[3].startswith("TESTE") for linha in fb.inseridos)
    sem_cpf = [linha for linha in fb.inseridos if linha[2] == ""]
    assert len(sem_cpf) == len(sem_doc) - 1 and all(linha[1] == "" for linha in sem_cpf)  # sem CPF e sem CNS
    assert len({linha[0] for linha in fb.inseridos}) == len(fb.inseridos)            # IDs sem repetir


def test_preview_conta_sem_documento(monkeypatch):
    monkeypatch.setattr(postgres, "POSTGRES_FALSO", JSON)
    sem_doc = [p for p in PACIENTES if not p["num_cpf"]]
    validos = [p for p in PACIENTES if bpa.valida_cpf(p["num_cpf"])]
    fb = _FbFalso(validos[5]["num_cpf"], "", sem_doc[0])
    monkeypatch.setattr(bpa, "conectar", lambda: fb)
    meses = sorted({a[:7].replace("-", "") for p in PACIENTES for a in p["atendimentos"]})
    total_sem_doc = 0
    for mes in meses:
        r = migracao.preview({"mes": mes})
        assert r["ok"]
        total_sem_doc += r["sem_documento"]
    assert total_sem_doc >= len(sem_doc) - 1
