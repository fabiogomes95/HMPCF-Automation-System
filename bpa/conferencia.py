"""
Conferência: compara os CPFs digitados nos arquivos de lote
(BPA_LOTES_DIR/DD-MM-AAAA.txt) com o que realmente está no lote de produção
do Firebird (tabela S_PRD, já importado no BPA Magnético), por dia e por
profissional (médico/enfermeiro).

Usa a mesma leitura/deduplicação de bpa_gerador.ler_arquivo_lote (descarta
"digitação dupla acidental" em sequência) — reflete exatamente o que o
"Gerar BPA-I" já usa, então não acusa como divergência uma duplicidade que o
próprio sistema já ignora silenciosamente.

Uso:
    python conferencia.py                          # últimos 7 dias corridos
    python conferencia.py 01/06/2026 07/06/2026     # período específico
    python conferencia.py --relatorio               # idem, salva .txt (CPF mascarado)
                                                      # em conferencia_relatorios/
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import bpa_gerador as bpa

BASE = Path(__file__).resolve().parent
RELATORIOS_DIR = BASE / "conferencia_relatorios"


def periodo_padrao() -> tuple[date, date]:
    """Últimos 7 dias corridos (hoje - 6 até hoje) — usado quando nenhum período é informado."""
    hoje = date.today()
    return hoje - timedelta(days=6), hoje


def _arquivos_lote_no_periodo(data_ini: date, data_fim: date) -> list[tuple[date, str]]:
    """Lista arquivos DD-MM-AAAA.txt na raiz de BPA_LOTES_DIR (sem subpastas de arquivo
    morto) cuja data cai no período. Ignora os BPA_MEDICOS_*/BPA_ENFERMEIROS_* (esses são
    a exportação, não o digitado)."""
    pasta = bpa.garantir_pasta_lotes()
    achados = []
    if not Path(pasta).is_dir():
        return achados
    for caminho in Path(pasta).iterdir():
        if not caminho.is_file() or caminho.suffix.lower() != ".txt":
            continue
        if caminho.name.upper().startswith("BPA_"):
            continue
        try:
            dt = datetime.strptime(caminho.stem, "%d-%m-%Y").date()
        except ValueError:
            continue
        if data_ini <= dt <= data_fim:
            achados.append((dt, caminho.name))
    achados.sort()
    return achados


def _resolver_cns(con, profs_raw: list[tuple[str, str]], grupo: dict) -> str:
    """CNS do cabeçalho do bloco, ou resolvido pelo nome se o lote for antigo/sem CNS."""
    cns_raw = (grupo.get("cns") or "").strip()
    if cns_raw:
        return cns_raw
    res = bpa.resolver_profissional_por_nome(profs_raw, grupo["medico_raw"])
    return res["cns"] if res["status"] == "auto" else ""


def conferir_dia(dt: date, nome_arquivo: str, con, profs_raw: list[tuple[str, str]]) -> dict:
    """Compara um dia: digitado (já deduplicado) x banco (S_PRD)."""
    caminho = bpa.caminho_lote(nome_arquivo)
    grupos = bpa.ler_arquivo_lote(caminho)

    cur = con.cursor()
    dtaten = dt.strftime("%Y%m%d")
    cur.execute("SELECT PRD_CNSMED, PRD_CPF_PCNTE FROM S_PRD WHERE PRD_DTATEN = ?", (dtaten,))
    banco_por_cns: dict[str, list[str]] = {}
    for cns, cpf in cur.fetchall():
        banco_por_cns.setdefault((cns or "").strip(), []).append((cpf or "").strip())

    profissionais = []
    total_digitado = total_banco = 0
    for g in grupos:
        cns = _resolver_cns(con, profs_raw, g)
        digitado = g["documentos"]
        no_banco = banco_por_cns.get(cns, [])
        c_dig, c_bd = Counter(digitado), Counter(no_banco)
        faltando = sorted((c_dig - c_bd).elements())
        sobrando = sorted((c_bd - c_dig).elements())
        total_digitado += len(digitado)
        total_banco += len(no_banco)
        profissionais.append({
            "nome": g["medico_raw"], "cns": cns,
            "digitado": len(digitado), "banco": len(no_banco),
            "ok": not faltando and not sobrando,
            "faltando_no_banco": faltando,
            "sobrando_no_banco": sobrando,
        })

    return {
        "data": dt.strftime("%d/%m/%Y"),
        "arquivo": nome_arquivo,
        "total_digitado": total_digitado,
        "total_banco": total_banco,
        "ok": total_digitado == total_banco and all(p["ok"] for p in profissionais),
        "profissionais": profissionais,
    }


def conferir_periodo(data_ini: date, data_fim: date) -> dict:
    arquivos = _arquivos_lote_no_periodo(data_ini, data_fim)
    base = {
        "data_ini": data_ini.strftime("%d/%m/%Y"),
        "data_fim": data_fim.strftime("%d/%m/%Y"),
        "dias": [], "total_digitado": 0, "total_banco": 0, "ok": True,
    }
    if not arquivos:
        return base

    con = bpa.conectar()
    try:
        profs_raw = bpa.listar_profissionais(con)
        dias = [conferir_dia(dt, nome, con, profs_raw) for dt, nome in arquivos]
    finally:
        con.close()

    return {
        **base,
        "dias": dias,
        "total_digitado": sum(d["total_digitado"] for d in dias),
        "total_banco": sum(d["total_banco"] for d in dias),
        "ok": all(d["ok"] for d in dias),
    }


# ── Relatório em texto (CPF mascarado — não deixa documento completo em texto
#    puro num arquivo persistido em disco; ver "Segurança" no README do projeto) ──
def _mascarar_cpf(cpf: str) -> str:
    if len(cpf) != 11:
        return "?" * len(cpf)
    return f"{cpf[:3]}.***.**{cpf[9:]}"


def formatar_relatorio_texto(resultado: dict, mascarar: bool = True) -> str:
    fmt_cpf = _mascarar_cpf if mascarar else (lambda c: c)
    linhas = [
        f"Conferencia BPA - digitado x lote de producao (Firebird)",
        f"Periodo: {resultado['data_ini']} a {resultado['data_fim']}",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "=" * 70,
    ]
    if not resultado["dias"]:
        linhas.append("Nenhum arquivo de lote digitado encontrado no periodo.")
        return "\n".join(linhas)

    for d in resultado["dias"]:
        status = "OK" if d["ok"] else "DIVERGENTE"
        linhas.append(
            f"\n[{status}] {d['data']} ({d['arquivo']}) "
            f"- digitado={d['total_digitado']}  banco={d['total_banco']}"
        )
        for p in d["profissionais"]:
            if p["ok"]:
                continue
            linhas.append(f"    {p['nome']} (CNS {p['cns']}): digitado={p['digitado']} banco={p['banco']}")
            if p["faltando_no_banco"]:
                cpfs = ", ".join(fmt_cpf(c) for c in p["faltando_no_banco"])
                linhas.append(f"        faltando no banco ({len(p['faltando_no_banco'])}): {cpfs}")
            if p["sobrando_no_banco"]:
                cpfs = ", ".join(fmt_cpf(c) for c in p["sobrando_no_banco"])
                linhas.append(f"        no banco mas sem correspondencia no arquivo ({len(p['sobrando_no_banco'])}): {cpfs}")

    linhas.append("\n" + "=" * 70)
    linhas.append(f"TOTAL digitado: {resultado['total_digitado']}   TOTAL banco: {resultado['total_banco']}")
    linhas.append("Situacao geral: " + ("tudo bate." if resultado["ok"] else "ha divergencias - ver acima."))
    return "\n".join(linhas)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    salvar_relatorio = "--relatorio" in sys.argv

    if len(args) >= 2:
        data_ini = datetime.strptime(args[0], "%d/%m/%Y").date()
        data_fim = datetime.strptime(args[1], "%d/%m/%Y").date()
    else:
        data_ini, data_fim = periodo_padrao()

    resultado = conferir_periodo(data_ini, data_fim)

    print(formatar_relatorio_texto(resultado, mascarar=False))

    if salvar_relatorio:
        RELATORIOS_DIR.mkdir(exist_ok=True)
        nome = f"conferencia_{date.today().strftime('%Y%m%d')}.txt"
        texto_mascarado = formatar_relatorio_texto(resultado, mascarar=True)
        (RELATORIOS_DIR / nome).write_text(texto_mascarado, encoding="utf-8")
        print(f"\nRelatorio salvo em: {RELATORIOS_DIR / nome}")

    sys.exit(0 if resultado["ok"] else 1)


if __name__ == "__main__":
    main()
