"""Conferência (digitado x S_PRD), incluindo paciente SEM CPF digitado pelo
cadastro ("ID:n") e comparado por nome + nascimento."""
from datetime import date
from pathlib import Path

import bpa_gerador as bpa
import conferencia


class _Con:
    def __init__(self, s_prd, cadcns):
        self.s_prd, self.cadcns = s_prd, cadcns

    def cursor(self):
        con = self

        class C:
            def execute(self, sql, params=None):
                if "FROM S_PRD" in sql:
                    self._r = con.s_prd
                elif "FROM CADCNS" in sql:
                    self._r = [r for r in con.cadcns if r[0] in params]

            def fetchall(self):
                return self._r
        return C()


def test_conferencia_com_paciente_sem_cpf(monkeypatch, tmp_path):
    monkeypatch.setattr(bpa, "BPA_LOTES_DIR", str(tmp_path))
    Path(tmp_path, "08-09-2026.txt").write_text(
        "PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 08/09/2026\n"
        "12345678909\nID:501\nID:502\n", encoding="utf-8")
    cadcns = [(501, "TESTE SEM DOC UM", "19900101"), (502, "TESTE SEM DOC DOIS", "19850505")]
    # No BPA Magnético: o paciente com CPF + o 501 (sem CPF, espaços como no S_PRD); falta o 502
    s_prd = [("111111111111111", "12345678909", "X", "19700101"),
             ("111111111111111", "", "TESTE SEM DOC UM".ljust(30), "19900101")]
    dia = conferencia.conferir_dia(date(2026, 9, 8), "08-09-2026.txt", _Con(s_prd, cadcns), [])
    p = dia["profissionais"][0]
    assert p["digitado"] == 3 and p["banco"] == 2
    assert p["faltando_no_banco"] == ["ID:502"]                # volta como digitado: o reenviar usa
    assert p["rotulos"] == {"ID:502": "sem CPF: TESTE SEM DOC DOIS (05/05/1985)"}
    assert p["sobrando_no_banco"] == [] and not p["ok"]


def test_conferencia_so_com_cpf_continua_igual(monkeypatch, tmp_path):
    monkeypatch.setattr(bpa, "BPA_LOTES_DIR", str(tmp_path))
    Path(tmp_path, "09-09-2026.txt").write_text(
        "PROFISSIONAL: DR MEDICO | CNS: 111111111111111 | DATA: 09/09/2026\n12345678909\n", encoding="utf-8")
    s_prd = [("111111111111111", "12345678909", "X", "19700101"), ("111111111111111", "98765432100", "Y", "19700101")]
    p = conferencia.conferir_dia(date(2026, 9, 9), "09-09-2026.txt", _Con(s_prd, []), [])["profissionais"][0]
    assert p["ok"] and p["faltando_no_banco"] == [] and p["sobrando_no_banco"] == ["98765432100"]
