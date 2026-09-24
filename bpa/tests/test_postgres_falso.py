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
    assert {l[1] for l in linhas} == esperados
    assert len(linhas[0]) == 15  # mesmas colunas da consulta real


class _FbFalso:
    """Firebird em memória: CADCNS com 1 paciente que já existe e 1 só com CNS."""

    def __init__(self, ja_tem_cpf: str, so_cns: str):
        self.cadcns = [(1, "", ja_tem_cpf), (2, so_cns, "")]
        self.inseridos, self.atualizados = [], []

    def cursor(self):
        fb = self

        class C:
            def execute(self, sql, params=None):
                if sql.startswith("SELECT MAX"):
                    self._r = [(max(i for i, _, _ in fb.cadcns),)]
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
    ja_tem = validos[5]
    so_cns = next(p for p in validos[6:] if p["cns"])
    fb = _FbFalso(ja_tem["num_cpf"], so_cns["cns"])
    monkeypatch.setattr(bpa, "conectar", lambda: fb)

    hoje = date.today()
    inicio = date(2000, 1, 1)  # todos os atendimentos do arquivo
    eventos = list(migracao.migrar(postgres.query_pacientes_periodo(inicio, hoje.replace(year=hoje.year + 1))))
    fim = eventos[-1]
    assert fim["tipo"] == "fim"

    total = len({p["num_cpf"] for p in PACIENTES})
    assert fim["cpf_invalidos"] == 2                     # os 2 CPFs inválidos de propósito
    assert fim["duplicatas"] == 1                        # quem já estava no Firebird
    assert fim["atualizados"] == 1 and fb.atualizados[0][0] == so_cns["num_cpf"]  # completou CPF pelo SUS
    assert fim["inseridos"] == total - 2 - 1 - 1
    assert all(linha[2] and linha[3].startswith("TESTE") for linha in fb.inseridos)  # CPF + nome
    assert len({linha[0] for linha in fb.inseridos}) == len(fb.inseridos)            # IDs sem repetir
