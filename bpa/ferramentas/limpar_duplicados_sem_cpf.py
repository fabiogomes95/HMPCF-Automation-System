"""
Apaga do Firebird (CADCNS) as cópias repetidas de paciente SEM CPF que a
migração criava até 30/09/2026: nome com espaço duplo e mais de 30 letras não
batia na conferência e o paciente era inserido de novo a cada migração.

Agrupa os cadastros sem CPF por nome (30 letras) + nascimento -- a mesma
identidade que a migração usa -- e em cada grupo mantém o de MENOR ID_CADCNS.
Também mantém qualquer cópia usada em lote de digitação ("ID:nnn").

Sem --apagar só mostra o que faria. Com --apagar grava antes um backup das
linhas em bpa/backup_cadcns_duplicados_AAAA-MM-DD.json.

Uso (na pasta do sistema, com o Python do BPA):
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\limpar_duplicados_sem_cpf.py            # só mostra
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\limpar_duplicados_sem_cpf.py --apagar   # apaga
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

BPA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BPA))

from bpa_local import config  # noqa: E402,F401  (carrega o bpa/.env)
import bpa_gerador as bpa  # noqa: E402
from bpa_local.services.migracao import chave_nome_nasc  # noqa: E402


def ids_usados_em_lotes() -> set[int]:
    usados: set[int] = set()
    pasta = Path(bpa.BPA_LOTES_DIR)
    for arq in pasta.rglob("*.txt") if pasta.is_dir() else []:
        texto = arq.read_text(encoding="utf-8", errors="replace")
        usados.update(int(n) for n in re.findall(r"\bID:(\d+)\b", texto))
    return usados


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apagar", action="store_true", help="apaga de verdade (sem isso só mostra)")
    args = ap.parse_args()

    fb = bpa.conectar()
    try:
        cur = fb.cursor()
        cur.execute("SELECT ID_CADCNS, NUM_CPF, NOME, DTNASC FROM CADCNS")
        grupos: dict[tuple, list[int]] = defaultdict(list)
        for id_, cpf, nome, dtnasc in cur.fetchall():
            chave = chave_nome_nasc(nome, dtnasc)
            if not (cpf or "").strip() and chave[0] and chave[1]:
                grupos[chave].append(id_)

        usados = ids_usados_em_lotes()
        apagar: list[int] = []
        for (nome, dtnasc), ids in sorted(grupos.items()):
            if len(ids) < 2:
                continue
            ids.sort()
            sai = [i for i in ids[1:] if i not in usados]
            print(f"{nome} ({dtnasc}): {len(ids)} cadastros -- mantém {ids[0]}"
                  + (f", apaga {len(sai)}: {sai}" if sai else ", nada a apagar (cópias usadas em lote)"))
            apagar += sai

        if not apagar:
            print("Nenhuma cópia repetida de paciente sem CPF. Nada a fazer.")
            return
        if not args.apagar:
            print(f"\n{len(apagar)} cadastro(s) seriam apagados. Rode de novo com --apagar para apagar.")
            return

        ph = ",".join("?" * len(apagar))
        cur.execute(f"SELECT * FROM CADCNS WHERE ID_CADCNS IN ({ph})", apagar)
        cols = [d[0] for d in cur.description]
        linhas = [dict(zip(cols, r)) for r in cur.fetchall()]
        backup = BPA / f"backup_cadcns_duplicados_{date.today().isoformat()}.json"
        backup.write_text(json.dumps(linhas, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        cur.execute(f"DELETE FROM CADCNS WHERE ID_CADCNS IN ({ph})", apagar)
        fb.commit()
        print(f"\n{len(apagar)} cadastro(s) apagado(s). Backup: {backup}")
        print("Reinicie o BPA local (ou rode o instalar.ps1) pra busca de pacientes recarregar.")
    finally:
        fb.close()


if __name__ == "__main__":
    main()
