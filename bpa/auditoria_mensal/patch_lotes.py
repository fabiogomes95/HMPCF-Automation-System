"""Patch pontual: insere na exportacao (BPA_MEDICOS_*/BPA_ENFERMEIROS_*) os
atendimentos que ja estao em S_PRD mas nao foram para o arquivo exportado
(lancados via /api/pacientes/completar ou /api/conferencia/reenviar, que
gravam em S_PRD sem tocar no arquivo exportado).

NAO mexe no banco (S_PRD) -- so le. NAO recalcula folha/seq -- usa o que
ja esta gravado em PRD_FLH/PRD_SEQ (a alocacao ja foi decidida e comitada
quando o registro foi inserido). So insere a linha dentro do bloco existente
do profissional (para nao alterar cbc-flh) e recalcula cbc-lin/cbc-smt-vrf
com a formula oficial ja validada (bpa_gerador._calcular_checksum).
"""
import sys, os
_BPA_DIR = os.path.dirname(os.path.abspath(__file__)) + r"\.."
sys.path.insert(0, _BPA_DIR)
os.chdir(_BPA_DIR)  # para achar .env

import bpa_gerador as bpa

LOTES_DIR = r"C:\BPA\bpa_lotes"  # pasta oficial dos lotes exportados (nao bpa.BPA_LOTES_DIR)

ALVOS = [
    # (dtaten AAAAMMDD, ddmmaaaa do nome do arquivo)
    ("20260608", "08062026"),
    ("20260616", "16062026"),
    ("20260621", "21062026"),
]

CATEGORIA_POR_CBO = {"225125": "medico", "223505": "enfermeiro"}
ROTULO = {"medico": "MEDICOS", "enfermeiro": "ENFERMEIROS"}


def ler_linhas_arquivo(caminho):
    with open(caminho, encoding="latin-1") as f:
        conteudo = f.read()
    linhas = [l for l in conteudo.splitlines() if l]
    header, detalhe = linhas[0], linhas[1:]
    return header, detalhe


def escrever_arquivo(caminho, header, detalhe):
    with open(caminho, "w", encoding="latin-1", newline="") as f:
        f.write(header + "\r\n")
        for l in detalhe:
            f.write(l + "\r\n")


def recalcular_n_folhas(detalhe):
    """Mesma logica do /api/gerar: soma, por bloco CONTIGUO de mesmo cnsmed,
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


def main(aplicar: bool):
    con = bpa.conectar()
    cur = con.cursor()

    plano = []  # (categoria, dtaten, ddmmaaaa, linha_pronta, cnsmed)

    for dtaten, ddmmaaaa in ALVOS:
        for categoria, cbo in [("medico", "225125"), ("enfermeiro", "223505")]:
            nome_arquivo = f"BPA_{ROTULO[categoria]}_{ddmmaaaa}.txt"
            caminho = os.path.join(LOTES_DIR, nome_arquivo)
            header, detalhe = ler_linhas_arquivo(caminho)

            existentes = set()
            for l in detalhe:
                existentes.add((l[15:30].strip(), l[49:59].strip(), l[59:74].strip()))  # cnsmed, pa, cnspac

            cur.execute(
                "SELECT PRD_CNSMED, PRD_PA, PRD_CNSPAC, PRD_FLH, PRD_SEQ, PRD_CPF_PCNTE, PRD_NMPAC "
                "FROM S_PRD WHERE PRD_DTATEN = ? AND PRD_CBO = ?",
                (dtaten, cbo),
            )
            for cnsmed, pa, cnspac, flh, seq, cpf, nome in cur.fetchall():
                cnsmed_s = (cnsmed or "").strip()
                pa_s = (pa or "").strip()
                cnspac_s = (cnspac or "").strip()
                chave = (cnsmed_s, pa_s, cnspac_s)
                if chave in existentes:
                    continue
                plano.append({
                    "categoria": categoria, "dtaten": dtaten, "ddmmaaaa": ddmmaaaa,
                    "arquivo": nome_arquivo, "caminho": caminho,
                    "cnsmed": cnsmed_s.zfill(15), "pa": pa_s.zfill(10), "cnspac": cnspac_s,
                    "flh": (flh or "").strip(), "seq": (seq or "").strip(),
                    "cpf": (cpf or "").strip(), "nome": (nome or "").strip(),
                })

    print(f"Total de linhas a inserir: {len(plano)}\n")
    for p in plano:
        print(f"  {p['arquivo']:35s} cnsmed={p['cnsmed']} pa={p['pa']} cnspac={p['cnspac']!r} "
              f"flh={p['flh']} seq={p['seq']} paciente={p['nome']}")

    if not plano:
        print("Nada a fazer.")
        return

    # documentos p/ busca no CADCNS (usa CNS se tiver, senao CPF)
    docs = []
    for p in plano:
        doc = p["cnspac"].strip() if p["cnspac"].strip() else p["cpf"].strip()
        docs.append(doc)
    pacientes, nao_encontrados, invalidos = bpa.buscar_pacientes(con, docs)
    if nao_encontrados or invalidos:
        print("\nATENCAO -- nao encontrados/invalidos na CADCNS:", nao_encontrados, invalidos)
        print("Abortando -- resolva isso antes de aplicar o patch.")
        return

    pac_por_doc = {}
    for doc, pac in zip(docs, pacientes):
        pac_por_doc[doc] = pac

    # monta as linhas prontas
    for p in plano:
        doc = p["cnspac"].strip() if p["cnspac"].strip() else p["cpf"].strip()
        pac = pac_por_doc[doc]
        proc = bpa.PROCEDIMENTOS[p["categoria"]]["codigo"]
        cbo = bpa.PROCEDIMENTOS[p["categoria"]]["cbo"]
        linha = bpa._linha_detalhe(
            pac, proc, cbo, p["cnsmed"], p["dtaten"], p["dtaten"][:6],
            int(p["flh"]), int(p["seq"]),
        )
        p["linha"] = linha

    print("\n--- Linhas construidas (conferir antes de aplicar) ---")
    for p in plano:
        print(f"[{p['arquivo']}] {p['linha']}")
        print(f"    len={len(p['linha'])}")

    if not aplicar:
        print("\n(dry-run -- nada foi escrito. rode com --aplicar para gravar)")
        return

    # agrupa por arquivo, insere dentro do bloco do profissional (ultima ocorrencia),
    # recalcula cabecalho, escreve
    por_arquivo = {}
    for p in plano:
        por_arquivo.setdefault(p["caminho"], []).append(p)

    for caminho, itens in por_arquivo.items():
        header, detalhe = ler_linhas_arquivo(caminho)
        for p in itens:
            cnsmed = p["cnsmed"]
            ultima_pos = None
            for idx, l in enumerate(detalhe):
                if l[15:30] == cnsmed:
                    ultima_pos = idx
            if ultima_pos is None:
                detalhe.append(p["linha"])
            else:
                detalhe.insert(ultima_pos + 1, p["linha"])

        n_linhas = len(detalhe)
        n_folhas = recalcular_n_folhas(detalhe)
        checksum = bpa._calcular_checksum(detalhe)
        competencia = detalhe[0][9:15]
        novo_header = bpa.montar_cabecalho(competencia, n_linhas, n_folhas, detalhe)
        # mantem exatamente o mesmo cabecalho, so troca lin/flh/checksum calculados
        escrever_arquivo(caminho, novo_header, detalhe)
        print(f"\nGravado: {caminho}")
        print(f"  linhas={n_linhas} folhas={n_folhas} checksum={checksum}")

    con.close()


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
