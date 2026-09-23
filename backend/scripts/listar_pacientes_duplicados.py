"""
listar_pacientes_duplicados.py
==============================
SOMENTE LEITURA -- não altera nem apaga nada.

Lista pacientes que parecem ser a mesma pessoa (mesmo nome + mesma data de
nascimento) cadastrados mais de uma vez. Caso típico: o bug em que o update
de paciente descartava o CPF, e a recepção criava um cadastro novo só com CPF
pra conseguir registrar -- ficando um cadastro "só SUS" e outro "só CPF".

Cada grupo mostra id, CPF, CNS, sem_documento e quantos atendimentos cada
cadastro tem, pra decidir manualmente como juntar.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\listar_pacientes_duplicados.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402

_SQL = text("""
    WITH base AS (
        SELECT p.id, p.nome, p.dtnasc, p.num_cpf, p.cns, p.sem_documento,
               UPPER(TRIM(p.nome)) AS nome_norm,
               (SELECT COUNT(*) FROM recepcao_atendimentos a WHERE a.paciente_id = p.id) AS atendimentos
        FROM pacientes p
        WHERE p.nome IS NOT NULL AND p.dtnasc IS NOT NULL
    ),
    grupos AS (
        SELECT nome_norm, dtnasc
        FROM base
        GROUP BY nome_norm, dtnasc
        HAVING COUNT(*) > 1
    )
    SELECT b.*
    FROM base b
    JOIN grupos g ON g.nome_norm = b.nome_norm AND g.dtnasc = b.dtnasc
    ORDER BY b.nome_norm, b.dtnasc, b.id
""")


def main() -> None:
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        rows = conn.execute(_SQL).mappings().all()

    if not rows:
        print("Nenhum paciente duplicado (nome + data de nascimento) encontrado.")
        return

    grupos: dict[tuple, list] = {}
    for r in rows:
        grupos.setdefault((r["nome_norm"], r["dtnasc"]), []).append(r)

    tipicos = 0
    for (nome, dtnasc), itens in grupos.items():
        so_cns = any(i["cns"] and not i["num_cpf"] for i in itens)
        so_cpf = any(i["num_cpf"] and not i["cns"] for i in itens)
        marca = "  <-- provável caso do bug (um só SUS, outro só CPF)" if so_cns and so_cpf else ""
        tipicos += bool(marca)
        print(f"\n{nome}  |  nasc {dtnasc}{marca}")
        for i in itens:
            print(
                f"   id={i['id']:<7} cpf={i['num_cpf'] or '-':<11}  cns={i['cns'] or '-':<15}  "
                f"sem_doc={'S' if i['sem_documento'] else 'N'}  atendimentos={i['atendimentos']}"
            )

    print(f"\nTotal: {len(grupos)} grupo(s) duplicado(s), {tipicos} no padrão do bug.")


if __name__ == "__main__":
    main()
