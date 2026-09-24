"""
importar_planilhas_recepcao.py
==============================
Carrega as planilhas manuais da recepção (Excel, ago/2021 em diante) na tabela
`atendimentos_planilha`, usada pela aba **Entradas** (em que dias o paciente
veio — pra achar o boletim impresso).

- As planilhas ficam FORA do repositório: C:\\HMPCF\\planilhas_manuais\\*.xlsx
  (têm nome/CPF de pacientes — nunca vão pro git; *.xlsx está no .gitignore).
- Recarrega tudo numa transação só: se der erro no meio, a tabela fica como estava.
- Rodar de novo quando chegar planilha nova ou corrigida.
- Regras de leitura (plantões, CPF, erros de digitação): app/importacao/planilhas_recepcao.py

Uso (pasta backend):
    .venv\\Scripts\\python scripts\\importar_planilhas_recepcao.py
    .venv\\Scripts\\python scripts\\importar_planilhas_recepcao.py --pasta D:\\outra\\pasta
    .venv\\Scripts\\python scripts\\importar_planilhas_recepcao.py --simular     # só lê e mostra o resumo
"""

import argparse
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.importacao.planilhas_recepcao import ler_pasta  # noqa: E402

PASTA_PADRAO = r"C:\HMPCF\planilhas_manuais"
COLUNAS = ("data", "hora", "nome", "nome_busca", "cpf", "cns", "nascimento", "arquivo", "aba", "linha")


def _campo(v) -> str:
    """Valor no formato texto do COPY (tab-separado; \\N = nulo)."""
    if v is None:
        return r"\N"
    return str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ").replace("\r", " ")


def main() -> None:
    ap = argparse.ArgumentParser(description="Importa as planilhas manuais da recepção.")
    ap.add_argument("--pasta", default=PASTA_PADRAO)
    ap.add_argument("--simular", action="store_true", help="só lê as planilhas e mostra o resumo")
    args = ap.parse_args()

    pasta = Path(args.pasta)
    if not pasta.is_dir() or not list(pasta.glob("*.xlsx")):
        sys.exit(f"Nenhuma planilha .xlsx em {pasta}")

    t0 = time.time()
    avisos: list[str] = []
    print(f"Lendo {pasta} ...")
    entradas, resumo = ler_pasta(pasta, avisos)

    for r in resumo:
        situacao = "pulada (mês já está em outra planilha)" if r["pulada"] else f"{r['novas']:>5} entradas"
        print(f"  {r['arquivo'][:32]:32} {r['aba']:20} {situacao}")
    if avisos:
        print(f"\n{len(avisos)} aviso(s) de dia fora de ordem (corrigidos pela sequência da aba):")
        for a in avisos:
            print("  -", a)
    com_cpf = sum(1 for e in entradas if e.cpf)
    print(f"\n{len(entradas)} entradas ({com_cpf} com CPF), "
          f"{min(e.data for e in entradas):%d/%m/%Y} a {max(e.data for e in entradas):%d/%m/%Y} "
          f"— lidas em {time.time() - t0:.0f}s")

    if args.simular:
        print("\n--simular: nada foi gravado.")
        return

    buf = io.StringIO()
    for e in entradas:
        linha = (e.data, e.hora, e.nome[:150], e.nome_busca[:150], e.cpf, e.cns, e.nascimento,
                 e.arquivo[:150], e.aba[:60], e.linha)
        buf.write("\t".join(_campo(v) for v in linha) + "\n")
    buf.seek(0)

    con = psycopg2.connect(host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
                           user=settings.POSTGRES_USER, password=settings.POSTGRES_PASSWORD,
                           dbname=settings.POSTGRES_DB)
    try:
        with con, con.cursor() as cur:  # uma transação: tudo ou nada
            cur.execute("DELETE FROM atendimentos_planilha")
            cur.copy_expert(f"COPY atendimentos_planilha ({', '.join(COLUNAS)}) FROM STDIN", buf)
            cur.execute("SELECT count(*) FROM atendimentos_planilha")
            total = cur.fetchone()[0]
        print(f"\nOK: {total} entradas gravadas em atendimentos_planilha ({time.time() - t0:.0f}s no total).")
    finally:
        con.close()


if __name__ == "__main__":
    main()
