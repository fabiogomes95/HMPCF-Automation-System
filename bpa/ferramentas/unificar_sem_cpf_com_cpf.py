"""
Unifica no Firebird o paciente com dois cadastros (um sem CPF + um com CPF).
Regras: bpa_local/services/unificar.py. Também tem botão na aba BPA › Migração
do sistema ("Pacientes em dobro no Firebird").

Sem --aplicar só mostra o que faria. Com --aplicar grava antes um backup em
bpa/backup_cadcns_unificados_*.json e faz tudo numa transação.

Uso (na pasta do sistema, com o Python do BPA):
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\unificar_sem_cpf_com_cpf.py             # só mostra
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\unificar_sem_cpf_com_cpf.py --aplicar   # corrige
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpa_local import config  # noqa: E402,F401  (carrega o bpa/.env)
from bpa_local.services import unificar  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aplicar", action="store_true", help="corrige de verdade (sem isso só mostra)")
    args = ap.parse_args()

    r = unificar.executar(aplicar=args.aplicar)
    if not r["ok"]:
        sys.exit(r["erro"])
    for a in r["acoes"]:
        print(f"{a['nome']}: fica {a['fica']} (recebe CPF {a['cpf']}), sai {a['sai']}")
    for av in r["avisos"]:
        print("  conferir à mão:", av)
    for g in r["cpfs_diferentes"]:
        print(f"  CPFs diferentes (conferir à mão): {g['nome']} ({g['nascimento']}) {g['cadastros']}")
    if not r["acoes"]:
        print("Nenhum paciente com cadastro sem CPF + com CPF. Nada a fazer.")
    elif r["aplicado"]:
        print(f"\n{r['total']} paciente(s) unificados. Backup: {r['backup']}")
    else:
        print(f"\n{r['total']} paciente(s) seriam unificados. Rode de novo com --aplicar para corrigir.")


if __name__ == "__main__":
    main()
