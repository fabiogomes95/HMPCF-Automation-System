"""MODO DE TESTE: faz o papel do PostgreSQL do hospital lendo pacientes FALSOS
de um arquivo JSON (bpa/teste/pacientes_falsos.json). Liga com
BPA_POSTGRES_FALSO=<caminho do json> no bpa/.env — serve pra testar a
migração em casa, contra um Firebird de TESTE. Nunca ligar num notebook de
produção: os pacientes iriam pro Firebird de verdade.

Entende só as duas consultas que o BPA faz: a lista de competências e os
pacientes atendidos num intervalo de datas (a mesma SQL de postgres.py)."""
import json
import re
from pathlib import Path

_RE_INICIO = re.compile(r"data_atendimento\s*>=\s*'(\d{4}-\d{2}-\d{2})'")
_RE_FIM = re.compile(r"data_atendimento\s*<\s*'(\d{4}-\d{2}-\d{2})'")
COLUNAS = ["cns", "num_cpf", "nome", "dtnasc", "sexo", "raca", "maepcn", "logpcn", "numpcn",
           "bairro_pcnte", "ceppcn", "ibge", "nacionalidade", "ddtel_pcnte", "tel_pcnte"]


class _Cursor:
    def __init__(self, pacientes: list[dict]) -> None:
        self._pacientes = pacientes
        self._linhas: list[tuple] = []

    def execute(self, sql: str, params=None) -> None:
        if "to_char" in sql:  # competências disponíveis
            meses = {a[:7].replace("-", "") for p in self._pacientes for a in p["atendimentos"]}
            self._linhas = [(m,) for m in sorted(meses, reverse=True)]
            return
        ini, fim = _RE_INICIO.search(sql), _RE_FIM.search(sql)
        if not ini or not fim:
            raise ValueError("postgres_falso: consulta não reconhecida")
        de, ate = ini.group(1), fim.group(1)
        vistos, linhas = set(), []
        for p in sorted(self._pacientes, key=lambda x: x["nome"]):
            if any(de <= a < ate for a in p["atendimentos"]):
                linha = tuple(p.get(c) or None for c in COLUNAS)
                if linha not in vistos:  # SELECT DISTINCT
                    vistos.add(linha)
                    linhas.append(linha)
        self._linhas = linhas

    def fetchall(self) -> list[tuple]:
        return list(self._linhas)


class ConexaoFalsa:
    def __init__(self, caminho: Path) -> None:
        self._pacientes = json.loads(caminho.read_text(encoding="utf-8"))["pacientes"]

    def cursor(self) -> _Cursor:
        return _Cursor(self._pacientes)

    def close(self) -> None:
        pass
