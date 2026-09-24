"""
Conferência: compara os CPFs digitados nos arquivos de lote
(BPA_LOTES_DIR/DD-MM-AAAA.txt) com o que realmente está no lote de produção
do Firebird (tabela S_PRD, já importado no BPA Magnético), por dia e por
profissional (médico/enfermeiro).

Usa a mesma leitura/deduplicação de bpa_gerador.ler_arquivo_lote (descarta
"digitação dupla acidental" em sequência) — reflete exatamente o que o
"Gerar BPA-I" já usa, então não acusa como divergência uma duplicidade que o
próprio sistema já ignora silenciosamente.

Usado pelas telas Conferência e Digitação ("No BPA Magnético: X de Y"). O
relatório semanal por linha de comando foi pro legado (legado/bpa_ferramentas).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import bpa_gerador as bpa



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


def _chave_sem_doc(nome, dtnasc) -> str:
    """Paciente SEM CPF (sem documento) não tem CPF pra comparar: usa nome
    (30 letras, como vai no BPA) + nascimento."""
    nome = " ".join(str(nome or "").upper().split())[:30].strip()
    return f"SD|{nome}|{str(dtnasc or '').strip()}"


def _rotulo_sem_doc(chave: str) -> str:
    _, nome, nasc = chave.split("|", 2)
    nasc_br = f"{nasc[6:8]}/{nasc[4:6]}/{nasc[:4]}" if len(nasc) == 8 else "?"
    return f"sem CPF: {nome} ({nasc_br})"


def _chaves_dos_ids(con, tokens: set[str]) -> dict[str, str]:
    """{"ID:n": chave nome+nascimento} dos pacientes digitados pelo cadastro."""
    ids = [int(t[len(bpa.PREFIXO_ID):]) for t in tokens]
    if not ids:
        return {}
    cur = con.cursor()
    cur.execute(f"SELECT ID_CADCNS, NOME, DTNASC FROM CADCNS WHERE ID_CADCNS IN ({','.join('?' * len(ids))})", ids)
    return {bpa.doc_por_id(i): _chave_sem_doc(nome, nasc) for i, nome, nasc in cur.fetchall()}


def conferir_dia(dt: date, nome_arquivo: str, con, profs_raw: list[tuple[str, str]]) -> dict:
    """Compara um dia: digitado (já deduplicado) x banco (S_PRD)."""
    caminho = bpa.caminho_lote(nome_arquivo)
    grupos = bpa.ler_arquivo_lote(caminho)

    # Paciente sem CPF foi digitado pelo cadastro ("ID:n") e entrou no S_PRD
    # sem CPF: os dois lados viram "nome + nascimento" pra comparar.
    tokens_id = {d for g in grupos for d in g["documentos"] if d.startswith(bpa.PREFIXO_ID)}
    chave_do_id = _chaves_dos_ids(con, tokens_id)

    cur = con.cursor()
    dtaten = dt.strftime("%Y%m%d")
    cur.execute("SELECT PRD_CNSMED, PRD_CPF_PCNTE, PRD_NMPAC, PRD_DTNASC FROM S_PRD WHERE PRD_DTATEN = ?", (dtaten,))
    banco_por_cns: dict[str, list[str]] = {}
    for cns, cpf, nome, nasc in cur.fetchall():
        cpf = (cpf or "").strip()
        banco_por_cns.setdefault((cns or "").strip(), []).append(cpf or _chave_sem_doc(nome, nasc))

    profissionais = []
    total_digitado = total_banco = 0
    for g in grupos:
        cns = _resolver_cns(con, profs_raw, g)
        digitado = g["documentos"]
        token_da_chave = {chave_do_id.get(d, d): d for d in digitado}
        chaves = [chave_do_id.get(d, d) for d in digitado]
        no_banco = banco_por_cns.get(cns, [])
        c_dig, c_bd = Counter(chaves), Counter(no_banco)
        # faltando volta como foi digitado ("ID:n" inclusive) -- o reenviar usa isso
        faltando = sorted(token_da_chave[k] for k in (c_dig - c_bd).elements())
        sobrando = sorted(_rotulo_sem_doc(k) if k.startswith("SD|") else k for k in (c_bd - c_dig).elements())
        rotulos = {t: _rotulo_sem_doc(chave_do_id[t]) for t in faltando if t in chave_do_id}
        total_digitado += len(digitado)
        total_banco += len(no_banco)
        profissionais.append({
            "nome": g["medico_raw"], "cns": cns,
            "digitado": len(digitado), "banco": len(no_banco),
            # "sobrando" (a mais no banco, sem correspondência no arquivo) não é
            # divergência — acontece quando um atendimento é lançado direto em
            # produção (ex: aba "Sem CPF"/"Reenviar Faltantes") sem passar pelo
            # arquivo digitado do dia. Só falta real (digitado e não achado no
            # banco) conta como problema.
            "ok": not faltando,
            "faltando_no_banco": faltando,
            "sobrando_no_banco": sobrando,
            "rotulos": rotulos,  # "ID:n" -> "sem CPF: NOME (nasc)", pra tela mostrar o nome
        })

    return {
        "data": dt.strftime("%d/%m/%Y"),
        "arquivo": nome_arquivo,
        "total_digitado": total_digitado,
        "total_banco": total_banco,
        "ok": all(p["ok"] for p in profissionais),
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
