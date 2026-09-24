"""Aba Entradas: em que dias o paciente deu entrada no hospital (e quantas vezes),
pra achar o boletim impresso — que é guardado por DATA.

Duas fontes, escolhidas na tela:
  - "sistema":   recepcao_atendimentos (o sistema, 2026 em diante)
  - "planilhas": atendimentos_planilha (planilhas manuais, ago/2021 em diante —
                 ver scripts/importar_planilhas_recepcao.py)
  - "ambos":     as duas; o mesmo dia nas duas fontes vira uma entrada só

Busca por CPF (11 dígitos), SUS (15) ou nome (sem acento, partes em ordem:
"MARIA SILVA" acha "MARIA DA SILVA"). Por CPF também traz as linhas da planilha
SEM CPF com o mesmo nome (2021 não tinha CPF; e às vezes ficou em branco) —
marcadas "pelo nome" pra conferir. Só leitura."""
import re
from collections import Counter
from datetime import date, datetime, time
from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.importacao.planilhas_recepcao import nome_busca

Fonte = Literal["ambos", "sistema", "planilhas"]

MAX_PESSOAS = 40
MAX_LINHAS = 20000
_JANELA_MIN = 90  # mesmo dia e até 90 min de diferença = a mesma entrada (sistema x planilha)

# nome do paciente no sistema, comparável com nome_busca (sem acento, maiúsculo)
_NOME_SISTEMA = (
    "translate(upper(p.nome), 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ', 'AAAAAEEEEIIIIOOOOOUUUUCN')"
)


def _criterio(q: str) -> tuple[str, str]:
    """('cpf'|'cns'|'nome', valor)."""
    digitos = re.sub(r"\D", "", q)
    letras = re.sub(r"[^A-Za-zÀ-ÿ]", "", q)
    if not letras and len(digitos) == 11:
        return "cpf", digitos
    if not letras and len(digitos) == 15:
        return "cns", digitos
    nb = nome_busca(q)
    if len(nb.replace(" ", "")) < 3:
        raise ValidationError("Digite o CPF (11 números), o SUS (15) ou pelo menos 3 letras do nome.")
    return "nome", "%" + nb.replace(" ", "%") + "%"


async def _do_sistema(session: AsyncSession, tipo: str, valor: str) -> list[dict]:
    filtro = {"cpf": "p.num_cpf = :v", "cns": "p.cns = :v", "nome": f"{_NOME_SISTEMA} LIKE :v"}[tipo]
    linhas = (await session.execute(text(f"""
        SELECT (ra.data_atendimento AT TIME ZONE 'America/Sao_Paulo') AS local,
               p.id, p.nome, p.num_cpf, p.cns, p.dtnasc
          FROM recepcao_atendimentos ra JOIN pacientes p ON p.id = ra.paciente_id
         WHERE {filtro}
         LIMIT {MAX_LINHAS}
    """), {"v": valor})).all()
    resultado = []
    for local, pid, nome, cpf, cns, dtnasc in linhas:
        nasc = None
        if dtnasc and len(dtnasc) == 8 and dtnasc.isdigit():
            try:
                nasc = date(int(dtnasc[:4]), int(dtnasc[4:6]), int(dtnasc[6:]))
            except ValueError:
                pass
        resultado.append({
            "data": local.date(), "hora": local.time().replace(second=0, microsecond=0),
            "nome": nome or "", "cpf": cpf or None, "cns": cns or None, "nascimento": nasc,
            "fonte": "sistema", "origem": "Sistema", "pelo_nome": False,
            "chave_sem_cpf": ("P", pid),
        })
    return resultado


async def _das_planilhas(session: AsyncSession, tipo: str, valor: str,
                         nomes_do_cpf: Optional[set[str]] = None) -> list[dict]:
    if nomes_do_cpf is not None:
        if not nomes_do_cpf:
            return []
        filtro, params = "cpf IS NULL AND nome_busca = ANY(:nomes)", {"nomes": list(nomes_do_cpf)}
    else:
        filtro = {"cpf": "cpf = :v", "cns": "cns = :v", "nome": "nome_busca LIKE :v"}[tipo]
        params = {"v": valor}
    linhas = (await session.execute(text(f"""
        SELECT data, hora, nome, nome_busca, cpf, cns, nascimento, arquivo, aba, linha
          FROM atendimentos_planilha WHERE {filtro} LIMIT {MAX_LINHAS}
    """), params)).all()
    return [{
        "data": d, "hora": h, "nome": nome, "cpf": cpf, "cns": cns, "nascimento": nasc,
        "fonte": "planilha", "origem": f"{arquivo} · {aba} · linha {linha}",
        "pelo_nome": nomes_do_cpf is not None, "chave_sem_cpf": ("N", nb, nasc),
    } for d, h, nome, nb, cpf, cns, nasc, arquivo, aba, linha in linhas]


def _minutos(h: Optional[time]) -> Optional[int]:
    return None if h is None else h.hour * 60 + h.minute


def _juntar(entradas: list[dict]) -> list[dict]:
    """Ordena e junta o mesmo atendimento vindo das duas fontes (mesmo dia, hora próxima)."""
    entradas.sort(key=lambda e: (e["data"], _minutos(e["hora"]) or 0))
    juntas: list[dict] = []
    for e in entradas:
        ult = juntas[-1] if juntas else None
        if (ult and ult["data"] == e["data"] and e["fonte"] not in ult["fontes"]
                and (ult["hora"] is None or e["hora"] is None
                     or abs(_minutos(ult["hora"]) - _minutos(e["hora"])) <= _JANELA_MIN)):
            ult["fontes"].append(e["fonte"])
            ult["origens"].append(e["origem"])
            ult["pelo_nome"] = ult["pelo_nome"] and e["pelo_nome"]
            continue
        juntas.append({"data": e["data"], "hora": e["hora"], "fontes": [e["fonte"]],
                       "origens": [e["origem"]], "pelo_nome": e["pelo_nome"]})
    return juntas


def _agrupar(linhas: list[dict]) -> list[dict]:
    """Uma pessoa por CPF; sem CPF, por nome+nascimento (planilha) ou cadastro (sistema).
    Linha sem CPF cujo nome é de UMA só pessoa com CPF entra nela, marcada "pelo nome"."""
    grupos: dict[tuple, list[dict]] = {}
    nome_para_cpf: dict[str, set[str]] = {}
    for e in linhas:
        if e["cpf"]:
            nome_para_cpf.setdefault(nome_busca(e["nome"]), set()).add(e["cpf"])
    for e in linhas:
        if e["cpf"]:
            chave = ("C", e["cpf"])
        else:
            cpfs = nome_para_cpf.get(nome_busca(e["nome"]), set())
            if len(cpfs) == 1:
                chave = ("C", next(iter(cpfs)))
                e = {**e, "pelo_nome": True}
            else:
                chave = e["chave_sem_cpf"]
        grupos.setdefault(chave, []).append(e)

    pessoas = []
    for chave, itens in grupos.items():
        entradas = _juntar(itens)
        nomes = Counter(i["nome"] for i in itens if i["nome"])
        nasc = Counter(i["nascimento"] for i in itens if i["nascimento"])
        cns = Counter(i["cns"] for i in itens if i["cns"])
        pessoas.append({
            "nome": nomes.most_common(1)[0][0] if nomes else "",
            "outros_nomes": [n for n, _ in nomes.most_common()[1:4]],
            "cpf": chave[1] if chave[0] == "C" else None,
            "cns": cns.most_common(1)[0][0] if cns else None,
            "nascimento": nasc.most_common(1)[0][0].isoformat() if nasc else None,
            "total": len(entradas),
            "primeira": entradas[0]["data"].isoformat(),
            "ultima": entradas[-1]["data"].isoformat(),
            "por_ano": dict(sorted(Counter(e["data"].year for e in entradas).items(), reverse=True)),
            "entradas": [{
                "data": e["data"].isoformat(),
                "hora": e["hora"].strftime("%H:%M") if e["hora"] else None,
                "fontes": e["fontes"], "origens": e["origens"], "pelo_nome": e["pelo_nome"],
            } for e in reversed(entradas)],
        })
    pessoas.sort(key=lambda p: (-p["total"], p["nome"]))
    return pessoas


async def resumo_planilhas(session: AsyncSession) -> dict:
    total, inicio, fim, importado = (await session.execute(text(
        "SELECT count(*), min(data), max(data), max(importado_em) FROM atendimentos_planilha"
    ))).one()
    return {
        "total": total,
        "inicio": inicio.isoformat() if inicio else None,
        "fim": fim.isoformat() if fim else None,
        "importado_em": importado.isoformat() if importado else None,
    }


async def buscar(session: AsyncSession, q: str, fonte: Fonte) -> dict:
    tipo, valor = _criterio((q or "").strip())
    linhas: list[dict] = []
    if fonte in ("ambos", "sistema"):
        linhas += await _do_sistema(session, tipo, valor)
    if fonte in ("ambos", "planilhas"):
        planilha = await _das_planilhas(session, tipo, valor)
        linhas += planilha
        if tipo == "cpf":
            # mesma pessoa em linhas da planilha que ficaram sem CPF
            nomes = {nome_busca(e["nome"]) for e in linhas if e["nome"]}
            linhas += await _das_planilhas(session, tipo, valor, nomes_do_cpf=nomes)

    pessoas = _agrupar(linhas)
    return {
        "criterio": tipo,
        "fonte": fonte,
        "pessoas": pessoas[:MAX_PESSOAS],
        "total_pessoas": len(pessoas),
        "limitado": len(pessoas) > MAX_PESSOAS,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
