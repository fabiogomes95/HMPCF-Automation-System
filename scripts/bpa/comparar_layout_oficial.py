"""
Compara um arquivo .MAR/.ABR ja exportado pelo BPA Magnetico com o layout
oficial do DATASUS (Layout_Exportacao_BPA.pdf), campo a campo.

Usado em 2026-06-18 para confirmar/corrigir o layout do gerar_bpa_i.py
contra C:\\BPA\\EXPORTA\\PAkauan-.MAR (export real de producao).

Apenas leitura do arquivo exportado. Nao toca no banco.

Uso:
    python comparar_layout_oficial.py "C:\\BPA\\EXPORTA\\PAkauan-.MAR"
"""

import sys

CABECALHO = [
    ("cbc-hdr",      0,   2),
    ("cbc-hdr2",     2,   7),
    ("cbc-mvm",      7,  13),
    ("cbc-lin",     13,  19),
    ("cbc-flh",     19,  25),
    ("cbc-smt-vrf", 25,  29),
    ("cbc-rsp",     29,  59),
    ("cbc-sgl",     59,  65),
    ("cbc-cgccpf",  65,  79),
    ("cbc-dst",     79, 119),
    ("cbc-dst-in", 119, 120),
    ("cbc_versao", 120, 130),
]

BPA_I = [
    ("prd-ident",        0,   2),
    ("prd-cnes",         2,   9),
    ("prd-cmp",          9,  15),
    ("prd_cnsmed",      15,  30),
    ("prd_cbo",         30,  36),
    ("prd_dtaten",      36,  44),
    ("prd-flh",         44,  47),
    ("prd-seq",         47,  49),
    ("prd-pa",          49,  59),
    ("prd-cnspac",      59,  74),
    ("prd-sexo",        74,  75),
    ("prd-ibge",        75,  81),
    ("prd-cid",         81,  85),
    ("prd-ldade",       85,  88),
    ("prd-qt",          88,  94),
    ("prd-caten",       94,  96),
    ("prd-naut",        96, 109),
    ("prd-org",        109, 112),
    ("prd-nmpac",      112, 142),
    ("prd-dtnasc",     142, 150),
    ("prd-raca",       150, 152),
    ("prd-etnia",      152, 156),
    ("prd-nac",        156, 159),
    ("prd_srv",        159, 162),
    ("prd_clf",        162, 165),
    ("prd_equipe_seq", 165, 173),
    ("prd_equipe_area",173, 177),
    ("prd_cnpj",       177, 191),
    ("prd_cep_pcnte",  191, 199),
    ("prd_lograd_pcnte",199, 202),
    ("prd_end_pcnte",  202, 232),
    ("prd_compl_pcnte",232, 242),
    ("prd_num_pcnte",  242, 247),
    ("prd_bairro_pcnte",247, 277),
    ("prd_ddtel_pcnte",277, 288),
    ("prd_email_pcnte",288, 328),
    ("prd_ine",        328, 338),
    ("prd_cpf_pcnte",  338, 349),
    ("prd_situacao_rua",349, 350),
]

if len(sys.argv) < 2:
    print("Uso: python comparar_layout_oficial.py <arquivo.MAR/.ABR>")
    sys.exit(1)

with open(sys.argv[1], encoding="latin-1", newline="") as f:
    linhas = [l.rstrip("\r\n") for l in f]

print(f"Total de linhas: {len(linhas)}")

print("\n=== CABEÇALHO (linha 0) ===")
h = linhas[0]
print(f"tamanho real: {len(h)}  (oficial sem CRLF: 130)")
for nome, ini, fim in CABECALHO:
    print(f"  [{ini:3}-{fim:3}] {nome:14} = {h[ini:fim]!r}")
print(f"  sobra apos posicao 130: {h[130:]!r}")

print("\n=== PRIMEIRAS 3 LINHAS DE DETALHE (tipo 03) ===")
detalhes = [l for l in linhas if l[:2] == "03"][:3]
for idx, d in enumerate(detalhes):
    print(f"\n--- detalhe {idx} (tamanho real: {len(d)}, oficial sem CRLF: 350) ---")
    for nome, ini, fim in BPA_I:
        print(f"  [{ini:3}-{fim:3}] {nome:18} = {d[ini:fim]!r}")
