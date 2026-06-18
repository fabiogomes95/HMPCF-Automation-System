"""
Verifica/reproduz o algoritmo de checksum (cbc-smt-vrf) do cabecalho BPA
contra um arquivo ja exportado, para confirmar a formula oficial.

Usado em 2026-06-18 para confirmar a formula contra
C:\\BPA\\EXPORTA\\PAkauan-.MAR (export real de producao): bateu exatamente.

Formula: soma(codigo_procedimento + quantidade) de todas as linhas de
detalhe, resto da divisao por 1111, + 1111.

Apenas leitura do arquivo exportado. Nao toca no banco.

Uso:
    python verificar_checksum.py "C:\\BPA\\EXPORTA\\PAkauan-.MAR"
"""

import sys

if len(sys.argv) < 2:
    print("Uso: python verificar_checksum.py <arquivo.MAR/.ABR>")
    sys.exit(1)

with open(sys.argv[1], encoding="latin-1", newline="") as f:
    linhas = [l.rstrip("\r\n") for l in f]

header = linhas[0]
checksum_real = header[25:29]
print("Checksum no cabecalho real:", checksum_real)

detalhes = [l for l in linhas if l[:2] == "03"]
print("Qtde linhas de detalhe:", len(detalhes))

total = 0
for d in detalhes:
    pa = int(d[49:59])
    qt = int(d[88:94])
    total += pa + qt

resto      = total % 1111
calculado  = resto + 1111
print("Soma total (pa+qt):", total)
print("Resto da divisao por 1111:", resto)
print("Checksum calculado (resto + 1111):", calculado)
print("Bate com o real?", str(calculado).zfill(4) == checksum_real)
