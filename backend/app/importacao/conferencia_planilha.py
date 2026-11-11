"""Conferência da planilha da recepção (Excel das meninas) contra o sistema.

Quando o sistema fica fora (ex.: 03/11/2026 17:30 → 04/11 08:30) a recepção
anota tudo só na planilha. Aqui a planilha é lida e comparada com os
atendimentos do banco; o que está na planilha e não está no sistema volta como
"faltando", pronto pra ser lançado (paciente novo + entrada com data, hora e
registro da planilha) por app/services/conferencia_planilha_service.py.

Leitura de dia/plantão/nome/CPF/SUS/nascimento: a mesma das Entradas
(app/importacao/planilhas_recepcao.py). Os outros campos (sexo, raça,
município, endereço, telefone e o nº de registro da coluna A) seguem o layout
de mar/2024 em diante:
    A nº  B nome  C nascimento  D idade  E sexo  F raça  G município  H hora
    I CPF  J SUS  K —  L endereço  M telefone
"""
from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Optional

from app.importacao.planilhas_recepcao import Entrada, ano_das_abas, ler_aba, mes_da_aba, nome_busca, sem_acento

RACAS = {"BRANCA": "01", "PRETA": "02", "PARDA": "03", "AMARELA": "04", "INDIGENA": "05"}
# Nome que não é de ninguém: a linha nunca vira cadastro, mesmo com outros dados.
_NOME_GENERICO = re.compile(r"^(PACIENTE|SEM NOME|NAO IDENTIFICAD|DESCONHECID|IGNORAD)")
_RE_TEL = re.compile(r"\(?\s*(\d{2})\s*\)?\s*(\d{4,5})\s*-?\s*(\d{4})")


@dataclass
class LinhaPlanilha:
    entrada: Entrada
    registro: Optional[int] = None
    sexo: Optional[str] = None        # M | F
    raca: Optional[str] = None        # código BPA ("03")
    municipio: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None    # só dígitos (DDD + número)

    # atalhos
    @property
    def data(self) -> date:
        return self.entrada.data

    @property
    def hora(self) -> Optional[time]:
        return self.entrada.hora

    @property
    def nome(self) -> str:
        return self.entrada.nome

    @property
    def quando(self) -> Optional[datetime]:
        return datetime.combine(self.data, self.hora) if self.hora else None

    def tem_dados_alem_do_nome(self) -> bool:
        e = self.entrada
        return any((e.cpf, e.cns, e.nascimento, self.sexo, self.endereco, self.telefone))

    def nome_generico(self) -> bool:
        return bool(_NOME_GENERICO.match(nome_busca(self.nome)))


@dataclass
class Leitura:
    abas_disponiveis: list[str]
    abas_lidas: list[str]
    linhas: list[LinhaPlanilha] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _texto(v) -> Optional[str]:
    if v is None or isinstance(v, (datetime, date, time)):
        return None
    s = " ".join(str(v).split()).upper()
    return s or None


def _extras(celulas: list) -> dict:
    c = list(celulas) + [None] * max(0, 13 - len(celulas))
    registro = int(c[0]) if isinstance(c[0], (int, float)) and not isinstance(c[0], bool) and 0 < c[0] < 10000 else None
    sexo = _texto(c[4])
    sexo = sexo[0] if sexo and sexo[0] in "MF" and len(sexo) <= 9 else None
    raca = RACAS.get(sem_acento(_texto(c[5]) or ""))
    municipio = _texto(c[6])
    if municipio:
        municipio = re.sub(r"\s*[-/]\s*RN$", "", sem_acento(municipio)).strip() or None
    tel = None
    m = _RE_TEL.search(str(c[12] or ""))
    if m:
        tel = "".join(m.groups())
    return {"registro": registro, "sexo": sexo, "raca": raca, "municipio": municipio,
            "endereco": _texto(c[11]), "telefone": tel}


def abas_de_mes(nomes: list[str]) -> list[tuple[str, int, int]]:
    """(aba, ano, mês) das abas que são de um mês, na ordem do arquivo."""
    anos = ano_das_abas(nomes)
    saida = []
    for n in nomes:
        mes, _ = mes_da_aba(n)
        if mes and anos.get(n):
            saida.append((n, anos[n], mes))
    return saida


def ler_planilha(conteudo: bytes, abas: Optional[list[str]] = None) -> Leitura:
    """Lê o .xlsx. Sem `abas`, lê as duas últimas abas de mês (mês atual + o anterior)."""
    import openpyxl

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        meses = abas_de_mes(wb.sheetnames)
        disponiveis = [n for n, _, _ in meses]
        if abas:
            escolhidas = [n for n in disponiveis if n in set(abas)]
        else:
            escolhidas = [n for n, _, _ in sorted(meses, key=lambda x: (x[1], x[2]))[-2:]]
        ano_de = {n: a for n, a, _ in meses}
        leitura = Leitura(disponiveis, escolhidas)
        vistos: set = set()
        for aba in escolhidas:
            linhas = [list(r) for r in wb[aba].iter_rows(values_only=True)]
            for e in ler_aba(linhas, aba, ano_de[aba], leitura.avisos):
                chave = (e.data, e.hora, e.nome_busca[:30])
                if chave in vistos:  # a virada do mês às vezes aparece nas duas abas
                    continue
                vistos.add(chave)
                leitura.linhas.append(LinhaPlanilha(e, **_extras(linhas[e.linha - 1][:20])))
        return leitura
    finally:
        wb.close()


@dataclass
class AtendimentoSistema:
    id: int
    quando: datetime          # horário de Brasília, sem fuso
    cpf: Optional[str]
    cns: Optional[str]
    nome_busca: str


def faltando_no_sistema(linhas: list[LinhaPlanilha], atendimentos: list[AtendimentoSistema]) -> list[LinhaPlanilha]:
    """Linhas da planilha sem atendimento correspondente no sistema.

    Correspondência = mesmo paciente (CPF, SUS ou nome) com até 1 dia de
    diferença (hora digitada errada, plantão trocado); cada atendimento do
    sistema só vale pra uma linha, e fica o mais próximo no tempo -- assim o
    paciente que voltou no dia seguinte não "some" atrás da primeira vinda."""
    indice: dict[tuple, list[int]] = {}
    for i, a in enumerate(atendimentos):
        for chave in (("cpf", a.cpf), ("cns", a.cns), ("nome", a.nome_busca)):
            if chave[1]:
                indice.setdefault(chave, []).append(i)

    usados: set[int] = set()
    faltando = []
    for ln in sorted(linhas, key=lambda x: (x.data, x.hora or time.min)):
        e = ln.entrada
        candidatos: set[int] = set()
        for chave in (("cpf", e.cpf), ("cns", e.cns), ("nome", e.nome_busca)):
            if chave[1]:
                candidatos.update(indice.get(chave, ()))
        alvo = ln.quando or datetime.combine(ln.data, time(12, 0))
        melhor = None
        for i in candidatos - usados:
            if abs((atendimentos[i].quando.date() - ln.data).days) > 1:
                continue
            dist = abs((atendimentos[i].quando - alvo).total_seconds())
            if melhor is None or dist < melhor[0]:
                melhor = (dist, i)
        if melhor:
            usados.add(melhor[1])
        else:
            faltando.append(ln)
    return faltando


def separar_endereco(endereco: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """'RUA X, 12 - BAIRRO' -> ('RUA X', '12', 'BAIRRO')."""
    if not endereco:
        return None, None, None
    s, bairro = (endereco.rsplit(" - ", 1) + [None])[:2] if " - " in endereco else (endereco, None)
    numero = None
    if "," in s:
        s, numero = (x.strip() for x in s.rsplit(",", 1))
    return (s.strip() or None), (numero or None), (bairro.strip() if bairro else None)
