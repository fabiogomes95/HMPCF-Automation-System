"""
Fechamento de mês — 4 checagens automáticas sobre uma competência (AAAAMM),
pensadas pra rodar antes de fechar o faturamento SUS do mês. Todas são
só-leitura (nenhuma grava nada) — ver auditoria_mensal/patch_lotes.py e
auditoria_mensal/fix_colisoes.py para as correções que essas checagens
apontam a necessidade de aplicar.

1. checar_export      — S_PRD x arquivo já exportado (mesma lógica do
                         auditoria_mensal/patch_lotes.py, generalizada pra
                         qualquer competência em vez de ALVOS hardcoded)
2. checar_colisoes    — (PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ) duplicado
                         (mesma lógica do auditoria_mensal/fix_colisoes.py)
3. checar_duplicidade — paciente+procedimento+data repetido em S_PRD — só
                         reporta, exige revisão humana antes de qualquer
                         exclusão (pode ser atendimento legítimo repetido)
4. checar_checksum    — cbc-lin/cbc-flh/cbc-smt-vrf do header x conteúdo
                         real de cada arquivo já exportado

Uso via CLI:
    python fechamento_mes.py 062026
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import bpa_gerador as bpa

_ARQUIVO_RE = re.compile(r"^BPA_(MEDICOS|ENFERMEIROS)_(\d{2})(\d{2})(\d{4})\.txt$", re.IGNORECASE)


def _ler_arquivo(caminho: str) -> tuple[str, list[str]]:
    with open(caminho, encoding="latin-1") as f:
        conteudo = f.read()
    linhas = [l for l in conteudo.splitlines() if l]
    return linhas[0], linhas[1:]


def _recalcular_n_folhas(detalhe: list[str]) -> int:
    """Mesma lógica do /api/gerar: soma, por bloco contíguo de mesmo cnsmed,
    (max folha - min folha + 1)."""
    total = 0
    i = 0
    while i < len(detalhe):
        cnsmed = detalhe[i][15:30]
        j = i
        folhas_bloco = []
        while j < len(detalhe) and detalhe[j][15:30] == cnsmed:
            folhas_bloco.append(int(detalhe[j][44:47]))
            j += 1
        total += max(folhas_bloco) - min(folhas_bloco) + 1
        i = j
    return total


def _arquivos_da_competencia(competencia: str) -> list[dict]:
    """{"nome", "caminho", "categoria", "dtaten"(AAAAMMDD)} dos
    BPA_MEDICOS_*/BPA_ENFERMEIROS_* cujo dia cai na competência informada,
    na pasta oficial de exportação (bpa.BPA_LOTES_DIR)."""
    pasta = Path(bpa.BPA_LOTES_DIR)
    achados = []
    if not pasta.is_dir():
        return achados
    for caminho in pasta.iterdir():
        if not caminho.is_file():
            continue
        m = _ARQUIVO_RE.match(caminho.name)
        if not m:
            continue
        rotulo, dd, mm, aaaa = m.groups()
        if f"{aaaa}{mm}" != competencia:
            continue
        achados.append({
            "nome": caminho.name,
            "caminho": str(caminho),
            "categoria": "medico" if rotulo.upper() == "MEDICOS" else "enfermeiro",
            "dtaten": f"{aaaa}{mm}{dd}",
        })
    return sorted(achados, key=lambda a: a["nome"])


def checar_export(con, competencia: str) -> dict:
    """S_PRD x arquivo exportado, dia a dia. Só considera dias que já têm
    arquivo exportado — dia sem arquivo nenhum é "ainda não gerado", não é
    pendência de export (isso é papel do /api/gerar, não desta checagem)."""
    arquivos = _arquivos_da_competencia(competencia)
    pendentes = []
    cur = con.cursor()
    for arq in arquivos:
        cbo = bpa.PROCEDIMENTOS[arq["categoria"]]["cbo"]
        _, detalhe = _ler_arquivo(arq["caminho"])
        existentes = {
            (l[15:30].strip(), l[49:59].strip(), l[59:74].strip()) for l in detalhe
        }
        cur.execute(
            "SELECT PRD_CNSMED, PRD_PA, PRD_CNSPAC, PRD_NMPAC FROM S_PRD "
            "WHERE PRD_DTATEN = ? AND PRD_CBO = ?",
            (arq["dtaten"], cbo),
        )
        for cnsmed, pa, cnspac, nome in cur.fetchall():
            chave = ((cnsmed or "").strip(), (pa or "").strip(), (cnspac or "").strip())
            if chave in existentes:
                continue
            pendentes.append({
                "data": f"{arq['dtaten'][6:8]}/{arq['dtaten'][4:6]}/{arq['dtaten'][:4]}",
                "categoria": arq["categoria"], "arquivo": arq["nome"],
                "paciente": (nome or "").strip(),
            })
    return {"ok": not pendentes, "pendentes": pendentes}


def checar_colisoes(con, competencia: str) -> dict:
    """(PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ) duplicado dentro da competência."""
    cur = con.cursor()
    cur.execute(
        "SELECT PRD_CNSMED, PRD_FLH, PRD_SEQ, COUNT(*) FROM S_PRD "
        "WHERE PRD_MVM = ? GROUP BY PRD_CNSMED, PRD_FLH, PRD_SEQ HAVING COUNT(*) > 1",
        (competencia,),
    )
    slots = [
        {"cnsmed": (c or "").strip(), "folha": (f or "").strip(), "seq": (s or "").strip(), "qtd": q}
        for c, f, s, q in cur.fetchall()
    ]
    total_extra = sum(s["qtd"] - 1 for s in slots)
    return {"ok": not slots, "slots": slots, "total_registros_extra": total_extra}


def checar_duplicidade(con, competencia: str) -> dict:
    """Mesmo paciente+procedimento+data mais de uma vez em S_PRD — só
    reporta, exige revisão humana antes de qualquer exclusão (pode ser
    atendimento legítimo repetido, não dá pra decidir automaticamente)."""
    cur = con.cursor()
    cur.execute(
        "SELECT PRD_CNSPAC, PRD_PA, PRD_DTATEN, PRD_NMPAC, COUNT(*) FROM S_PRD "
        "WHERE PRD_CMP = ? GROUP BY PRD_CNSPAC, PRD_PA, PRD_DTATEN, PRD_NMPAC HAVING COUNT(*) > 1",
        (competencia,),
    )
    duplicados = [
        {
            "paciente": (nome or "").strip(), "cnspac": (cnspac or "").strip(),
            "pa": (pa or "").strip(),
            "data": f"{dt[6:8]}/{dt[4:6]}/{dt[:4]}" if dt else "",
            "qtd": q,
        }
        for cnspac, pa, dt, nome, q in cur.fetchall()
    ]
    return {"ok": not duplicados, "duplicados": duplicados}


def checar_checksum(competencia: str) -> dict:
    """Recalcula cbc-lin/cbc-flh/cbc-smt-vrf de cada arquivo já exportado da
    competência e compara com o que está gravado no header."""
    arquivos = _arquivos_da_competencia(competencia)
    divergentes = []
    for arq in arquivos:
        header, detalhe = _ler_arquivo(arq["caminho"])
        n_linhas_header = int(header[13:19])
        n_folhas_header = int(header[19:25])
        checksum_header = header[25:29]

        n_linhas_real = len(detalhe)
        n_folhas_real = _recalcular_n_folhas(detalhe)
        checksum_real = bpa._calcular_checksum(detalhe)

        diffs = {}
        if n_linhas_real != n_linhas_header:
            diffs["linhas"] = {"header": n_linhas_header, "real": n_linhas_real}
        if n_folhas_real != n_folhas_header:
            diffs["folhas"] = {"header": n_folhas_header, "real": n_folhas_real}
        if checksum_real != checksum_header:
            diffs["checksum"] = {"header": checksum_header, "real": checksum_real}
        if diffs:
            divergentes.append({"arquivo": arq["nome"], **diffs})
    return {"ok": not divergentes, "divergentes": divergentes}


def rodar(competencia: str) -> dict:
    con = bpa.conectar()
    try:
        export = checar_export(con, competencia)
        colisoes = checar_colisoes(con, competencia)
        duplicidade = checar_duplicidade(con, competencia)
    finally:
        con.close()
    checksum = checar_checksum(competencia)
    return {
        "competencia": competencia,
        "ok": export["ok"] and colisoes["ok"] and duplicidade["ok"] and checksum["ok"],
        "export": export, "colisoes": colisoes,
        "duplicidade": duplicidade, "checksum": checksum,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2 or not re.fullmatch(r"\d{6}", sys.argv[1]):
        print("Uso: python fechamento_mes.py AAAAMM")
        sys.exit(1)
    print(json.dumps(rodar(sys.argv[1]), ensure_ascii=False, indent=2))
