"""Unifica no Firebird (CADCNS) o paciente que ficou com DOIS cadastros: um sem
CPF (recepção cadastrou sem documento) e outro com CPF (a migração criava um
novo quando ele ganhava CPF -- corrigido em 11/11/2026: agora completa o
cadastro sem CPF, ver migracao.py).

Mesma pessoa = mesmo nome (30 letras) + mesmo nascimento (chave da migração).
Em cada grupo com cadastro(s) sem CPF e exatamente UM com CPF:
  - FICA o sem CPF mais antigo (menor ID_CADCNS -- pode estar num lote como
    "ID:nnn"), que recebe o CPF e os dados mais novos do cadastro com CPF;
  - SAI o cadastro com CPF (e outras cópias sem CPF).
A produção (S_PRD) guarda CPF/SUS/nome, não o ID -- nada nela muda.

Fica de fora (lista pra conferir à mão): cópia que sairia usada em lote.
Grupos com 2 CPFs diferentes também não são mexidos (qual é o certo?).

Usado pelo botão da aba BPA › Migração e por ferramentas/unificar_sem_cpf_com_cpf.py.
"""
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import bpa_gerador as bpa

from bpa_local import postgres
from bpa_local.cache import cache
from bpa_local.config import BASE
from bpa_local.services import migracao

COLUNAS = ["NOME", "SEXO", "RACA", "MAEPCN", "LOGPCN", "NUMPCN", "BAIRRO_PCNTE",
           "CEPPCN", "IBGE", "NACIONALIDADE", "DDTEL_PCNTE", "TEL_PCNTE"]


def ids_usados_em_lotes() -> set[int]:
    usados: set[int] = set()
    pasta = Path(bpa.BPA_LOTES_DIR)
    for arq in pasta.rglob("*.txt") if pasta.is_dir() else []:
        texto = arq.read_text(encoding="utf-8", errors="replace")
        usados.update(int(n) for n in re.findall(r"\bID:(\d+)\b", texto))
    return usados


def _cpf(ln: dict) -> str:
    return str(ln.get("NUM_CPF") or "").strip()


def cpfs_no_servidor(cpfs: set[str]) -> set[str] | None:
    """Quais desses CPFs existem hoje no cadastro do servidor (None = servidor fora)."""
    if not cpfs:
        return set()
    try:
        pg = postgres.conectar()
    except Exception:
        return None
    try:
        cur = pg.cursor()
        cur.execute("SELECT num_cpf FROM pacientes WHERE num_cpf = ANY(%s)", (sorted(cpfs),))
        return {r[0] for r in cur.fetchall()}
    finally:
        pg.close()


def planejar(linhas: list[dict], usados: set[int],
             no_servidor: set[str] | None = None) -> tuple[list[dict], list[str], list[dict]]:
    """(ações, avisos, cpfs_diferentes).
    Ação = {"fica": id, "sai": [ids], "cpf", "nome", "nascimento", "dados": {col: valor} | None}.

    Mesmo paciente com CPFs diferentes (decisão do usuário, 11/11/2026): vale o
    CPF que está HOJE no cadastro do servidor (o último que a recepção gravou);
    os cadastros com os outros CPFs saem. Se nenhum ou mais de um CPF estiver
    no servidor (ou o servidor estiver fora), fica pra conferir à mão."""
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for ln in linhas:
        chave = migracao.chave_nome_nasc(ln["NOME"], ln["DTNASC"])
        if chave[0] and chave[1]:
            grupos[chave].append(ln)

    acoes, avisos, cpfs_diferentes = [], [], []
    for (nome, nasc), grupo in sorted(grupos.items()):
        sem = sorted((g for g in grupo if not _cpf(g)), key=lambda g: g["ID_CADCNS"])
        com = [g for g in grupo if _cpf(g)]
        if len({_cpf(g) for g in com}) > 1:
            validos = {_cpf(g) for g in com} & (no_servidor or set())
            if len(validos) == 1:
                cpf = validos.pop()
                fica = min((g for g in com if _cpf(g) == cpf), key=lambda g: g["ID_CADCNS"])
                sai = [g["ID_CADCNS"] for g in com if g is not fica]
                acoes.append({"fica": fica["ID_CADCNS"], "sai": sai, "cpf": cpf, "nome": nome,
                              "nascimento": nasc, "dados": None, "motivo": "CPF antigo (servidor usa este)"})
                continue
            cpfs_diferentes.append({"nome": nome, "nascimento": nasc,
                                    "cadastros": [{"id": g["ID_CADCNS"], "cpf": _cpf(g)} for g in grupo]})
            continue
        if not sem or not com:
            continue
        fica, sai = sem[0], com + sem[1:]
        presos = [g["ID_CADCNS"] for g in sai if g["ID_CADCNS"] in usados]
        if presos:
            avisos.append(f"{nome} ({nasc}): cadastro(s) {presos} usado(s) em lote — conferir à mão")
            continue
        acoes.append({"fica": fica["ID_CADCNS"], "sai": [g["ID_CADCNS"] for g in sai], "cpf": _cpf(com[0]),
                      "nome": nome, "nascimento": nasc, "dados": {c: com[0].get(c) for c in COLUNAS},
                      "motivo": "sem CPF + com CPF"})
    return acoes, avisos, cpfs_diferentes


def _mae(ln: dict) -> str:
    return " ".join(str(ln.get("MAEPCN") or "").upper().split())


def candidatos_nasc_errado(linhas: list[dict]) -> list[tuple[dict, dict]]:
    """(sem CPF, com CPF) com mesmo nome e mesma mãe mas nascimento diferente --
    ex.: nascimento 02/04 (sem CPF) x 04/04 (com CPF): data digitada errada."""
    por_nome_mae: dict[tuple, list[dict]] = defaultdict(list)
    for ln in linhas:
        nome = migracao.chave_nome_nasc(ln["NOME"], "")[0]
        if nome and len(_mae(ln)) > 5:
            por_nome_mae[(nome, _mae(ln))].append(ln)
    pares = []
    for grupo in por_nome_mae.values():
        sem = [g for g in grupo if not _cpf(g)]
        com = [g for g in grupo if _cpf(g)]
        if len(sem) == 1 and len(com) == 1 and sem[0]["DTNASC"] != com[0]["DTNASC"]:
            pares.append((sem[0], com[0]))
    return pares


def sem_cpf_existe_no_servidor(sem: dict) -> bool | None:
    """O cadastro sem CPF (mesmo nome e nascimento) ainda existe no servidor? None = servidor fora."""
    nome, nasc = migracao.chave_nome_nasc(sem["NOME"], sem["DTNASC"])
    try:
        pg = postgres.conectar()
    except Exception:
        return None
    try:
        cur = pg.cursor()
        cur.execute("SELECT nome FROM pacientes WHERE dtnasc = %s AND (num_cpf IS NULL OR num_cpf = '') "
                    "AND upper(nome) LIKE %s", (nasc, nome.split()[0] + "%"))
        return any(migracao.chave_nome_nasc(n, nasc) == (nome, nasc) for (n,) in cur.fetchall())
    finally:
        pg.close()


def planejar_nasc_errado(pares: list[tuple[dict, dict]], usados: set[int], existe) -> tuple[list[dict], list[str]]:
    """Sai o cadastro sem CPF quando ele já não existe no servidor (a recepção
    ficou com o de CPF). `existe(sem)` -> True/False/None (servidor fora)."""
    acoes, avisos = [], []
    for sem, com in pares:
        nome = migracao.chave_nome_nasc(sem["NOME"], "")[0]
        no_servidor = existe(sem)
        if no_servidor is None or no_servidor:
            avisos.append(f"{nome}: nascimento {sem['DTNASC']} (sem CPF, ID {sem['ID_CADCNS']}) x "
                          f"{com['DTNASC']} (CPF {_cpf(com)}) — conferir à mão")
        elif sem["ID_CADCNS"] in usados:
            avisos.append(f"{nome}: cadastro sem CPF {sem['ID_CADCNS']} usado em lote — conferir à mão")
        else:
            acoes.append({"fica": com["ID_CADCNS"], "sai": [sem["ID_CADCNS"]], "cpf": _cpf(com), "nome": nome,
                          "nascimento": com["DTNASC"], "dados": None,
                          "motivo": f"nascimento errado ({sem['DTNASC']}) sem CPF"})
    return acoes, avisos


def executar(aplicar: bool = False) -> dict:
    """Sem aplicar: só mostra. Com aplicar: backup em bpa/backup_cadcns_unificados_*.json
    e tudo numa transação (erro = nada muda)."""
    if aplicar and not migracao.TRAVA.acquire(blocking=False):
        return {"ok": False, "erro": "Migração em andamento — tente de novo quando terminar."}
    try:
        fb = bpa.conectar()
    except Exception as e:
        if aplicar:
            migracao.TRAVA.release()
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}
    try:
        cur = fb.cursor()
        cur.execute("SELECT * FROM CADCNS")
        cols = [d[0].strip() for d in cur.description]
        linhas = [dict(zip(cols, r)) for r in cur.fetchall()]
        # CPFs de pacientes que aparecem com mais de um CPF: quais o servidor tem hoje
        por_chave: dict[tuple, set] = defaultdict(set)
        for ln in linhas:
            if _cpf(ln):
                por_chave[migracao.chave_nome_nasc(ln["NOME"], ln["DTNASC"])].add(_cpf(ln))
        duvidosos = set().union(*(c for c in por_chave.values() if len(c) > 1))
        no_servidor = cpfs_no_servidor(duvidosos)
        usados = ids_usados_em_lotes()
        acoes, avisos, cpfs_diferentes = planejar(linhas, usados, no_servidor)
        acoes_n, avisos_n = planejar_nasc_errado(candidatos_nasc_errado(linhas), usados, sem_cpf_existe_no_servidor)
        acoes += acoes_n
        avisos += avisos_n
        if no_servidor is None and duvidosos:
            avisos.append("Servidor fora do ar: pacientes com CPFs diferentes não foram conferidos agora.")
        resposta = {"ok": True, "aplicado": False, "total": len(acoes),
                    "acoes": [{k: v for k, v in a.items() if k != "dados"} for a in acoes],
                    "avisos": avisos, "cpfs_diferentes": cpfs_diferentes}
        if not aplicar or not acoes:
            return resposta

        ids = sorted({a["fica"] for a in acoes} | {i for a in acoes for i in a["sai"]})
        por_id = {ln["ID_CADCNS"]: ln for ln in linhas}
        backup = BASE / f"backup_cadcns_unificados_{datetime.now():%Y-%m-%d_%H%M%S}.json"
        backup.write_text(json.dumps({"acoes": acoes, "linhas_antes": [por_id[i] for i in ids]},
                                     ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        sql_update = f"UPDATE CADCNS SET NUM_CPF = ?, {', '.join(c + ' = ?' for c in COLUNAS)} WHERE ID_CADCNS = ?"
        try:
            for a in acoes:
                cur.execute(f"DELETE FROM CADCNS WHERE ID_CADCNS IN ({','.join('?' * len(a['sai']))})", a["sai"])
                if a["dados"] is not None:
                    cur.execute(sql_update, [a["cpf"], *[a["dados"][c] for c in COLUNAS], a["fica"]])
            fb.commit()
        except Exception as e:
            fb.rollback()
            return {"ok": False, "erro": f"Nada foi alterado (erro no Firebird): {e}"}
        cache.carregar_pacientes()
        resposta.update(aplicado=True, backup=str(backup))
        return resposta
    finally:
        fb.close()
        if aplicar:
            migracao.TRAVA.release()
