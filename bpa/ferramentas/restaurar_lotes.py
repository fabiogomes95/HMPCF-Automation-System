"""
Restaura os lotes de digitação do BPA guardados no servidor (tabela
bpa_lotes_backup) — pra quando um notebook quebrar ou perder os arquivos.

Usa a conexão do bpa/.env (usuário bpa_leitura). NUNCA sobrescreve lote
existente: grava numa pasta separada (padrão: bpa_lotes/restaurados_AAAA-MM-DD)
e você decide o que copiar de volta.

Uso (na pasta do sistema, com o Python do BPA):
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\restaurar_lotes.py                 # lista os notebooks
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\restaurar_lotes.py NOTEBOOK-1       # restaura os lotes dele
    bpa\\.venv\\Scripts\\python bpa\\ferramentas\\restaurar_lotes.py NOTEBOOK-1 --pasta C:\\BPA\\recuperados
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # bpa/

from bpa_local.services.backup_lotes import _conectar  # noqa: E402  (carrega o bpa/.env)
import bpa_gerador as bpa  # noqa: E402


def listar(cur) -> None:
    cur.execute("""
        SELECT notebook, count(*), max(recebido_em)
        FROM bpa_lotes_backup GROUP BY notebook ORDER BY notebook
    """)
    linhas = cur.fetchall()
    if not linhas:
        print("Nenhum lote guardado no servidor ainda.")
        return
    print("Notebooks com lotes guardados no servidor:")
    for notebook, qtd, ultimo in linhas:
        print(f"  {notebook:<25} {qtd:>4} lote(s)   último envio: {ultimo:%d/%m/%Y %H:%M}")
    print("\nPara restaurar: restaurar_lotes.py <NOTEBOOK>")


def restaurar(cur, notebook: str, pasta: Path) -> None:
    cur.execute("SELECT arquivo, conteudo FROM bpa_lotes_backup WHERE notebook = %s ORDER BY arquivo", (notebook,))
    lotes = cur.fetchall()
    if not lotes:
        print(f"Nenhum lote do notebook '{notebook}' no servidor (confira o nome com a lista).")
        return
    for arquivo, conteudo in lotes:
        destino = pasta / arquivo
        if destino.exists():
            print(f"  [PULEI] {arquivo} já existe em {pasta} (não sobrescrevo)")
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo.encode("utf-8"))  # conteúdo exato, com as quebras de linha originais
        print(f"  [OK] {arquivo}")
    print(f"\n{len(lotes)} lote(s) em {pasta}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Restaura lotes do BPA guardados no servidor.")
    ap.add_argument("notebook", nargs="?", help="nome do notebook (sem ele, só lista)")
    ap.add_argument("--pasta", help="onde gravar (padrão: bpa_lotes/restaurados_<hoje>)")
    args = ap.parse_args()

    con = _conectar()
    try:
        cur = con.cursor()
        if not args.notebook:
            listar(cur)
        else:
            pasta = Path(args.pasta) if args.pasta else Path(bpa.BPA_LOTES_DIR) / f"restaurados_{date.today():%Y-%m-%d}"
            restaurar(cur, args.notebook.upper(), pasta)
    finally:
        con.close()


if __name__ == "__main__":
    main()
