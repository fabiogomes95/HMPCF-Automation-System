"""
mesclar_pacientes_duplicados.py
===============================
Junta cadastros duplicados de pacientes (mesmo nome + mesma data de
nascimento) -- sobra do bug em que o update descartava o CPF e a recepção
criava um cadastro novo só com CPF.

Só mescla grupos SEM conflito de documento (no máximo 1 CPF distinto e no
máximo 1 CNS distinto no grupo). Grupos com CPFs ou CNSs diferentes são só
listados, pra decisão manual.

Nunca apaga paciente. Por grupo:
  - principal = o que tem CPF (CPF é o documento principal); empate → mais
    atendimentos → menor id
  - atendimentos dos outros cadastros passam pro principal
  - CNS vai pro principal se ele não tiver (sai do secundário antes, CNS é único)
  - campos vazios do principal são completados com os dos secundários
  - secundários ficam no banco, sem atendimentos (e sem o CNS movido)
  - tudo registrado em logs_auditoria (sem CPF/CNS, só metadados)

Antes de aplicar, salva backup JSON completo em backend/backups_mescla/
(pra desfazer à mão se precisar). Tudo numa transação só.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\mesclar_pacientes_duplicados.py            # só mostra (dry-run)
    .venv\\Scripts\\python scripts\\mesclar_pacientes_duplicados.py --aplicar  # grava
    ... --cns-divergente   # inclui grupos com CNSs diferentes (mas no máx. 1 CPF)
    ... --principal=1026,7662  # só esses grupos, com esses ids como principal
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402

_USUARIO_LOG = "script:mesclar_duplicados"

# Campos completados no principal quando estiverem vazios lá.
_CAMPOS_COMPLETAR = [
    "sexo", "raca", "maepcn", "logpcn", "numpcn", "bairro_pcnte",
    "ddtel_pcnte", "tel_pcnte", "nome_social", "civil", "ocupacao",
    "responsavel", "cidade", "estado", "naturalidade",
]

_SQL_GRUPOS = text("""
    WITH base AS (
        SELECT p.*, UPPER(TRIM(p.nome)) AS nome_norm,
               (SELECT COUNT(*) FROM recepcao_atendimentos a WHERE a.paciente_id = p.id) AS atendimentos
        FROM pacientes p
        WHERE p.nome IS NOT NULL AND p.dtnasc IS NOT NULL
          -- secundários já mesclados em execução anterior ficam de fora
          AND p.id NOT IN (
              SELECT l.recurso_id FROM logs_auditoria l
              WHERE l.recurso = 'paciente' AND l.usuario_username = :u
                AND CAST(l.campos_alterados AS TEXT) LIKE '%mescla_para_%'
          )
    ),
    grupos AS (
        SELECT nome_norm, dtnasc FROM base
        GROUP BY nome_norm, dtnasc HAVING COUNT(*) > 1
    )
    SELECT b.* FROM base b
    JOIN grupos g ON g.nome_norm = b.nome_norm AND g.dtnasc = b.dtnasc
    ORDER BY b.nome_norm, b.dtnasc, b.id
""")


def _vazio(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _serializavel(row: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}


def main() -> None:
    aplicar = "--aplicar" in sys.argv
    engine = create_engine(settings.database_url_sync)

    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(_SQL_GRUPOS, {"u": _USUARIO_LOG}).mappings().all()]
        grupos: dict[tuple, list[dict]] = {}
        for r in rows:
            grupos.setdefault((r["nome_norm"], r["dtnasc"]), []).append(r)

        # --cns-divergente: também mescla grupos em que só o CNS diverge (SUS é
        # complemento; o principal mantém o próprio CNS e o dos secundários
        # fica no cadastro antigo). CPFs diferentes nunca são mesclados.
        aceita_cns_divergente = "--cns-divergente" in sys.argv
        # --principal=ID,ID: mescla SÓ os grupos desses ids, com eles como
        # principal, mesmo com CPFs diferentes (decisão manual, conferida
        # com a recepção). O CPF descartado fica no cadastro antigo.
        forcados = {
            int(x)
            for a in sys.argv if a.startswith("--principal=")
            for x in a.split("=", 1)[1].split(",") if x.strip()
        }
        mesclaveis, conflitos = [], []
        for chave, itens in grupos.items():
            if forcados:
                fixo = [i for i in itens if i["id"] in forcados]
                if fixo:
                    itens.sort(key=lambda i: i["id"] != fixo[0]["id"])
                    mesclaveis.append((chave, itens))
                else:
                    conflitos.append((chave, itens))
                continue
            cpfs = {i["num_cpf"] for i in itens if i["num_cpf"]}
            cnss = {i["cns"] for i in itens if i["cns"]}
            ok = len(cpfs) <= 1 and (len(cnss) <= 1 or aceita_cns_divergente)
            (mesclaveis if ok else conflitos).append((chave, itens))

        backup = {"gerado_em": datetime.now().isoformat(), "grupos": []}
        total_atd = 0

        for (nome, dtnasc), itens in mesclaveis:
            if not forcados:
                itens.sort(key=lambda i: (not i["num_cpf"], -i["atendimentos"], i["id"]))
            principal, secundarios = itens[0], itens[1:]
            ids_sec = [s["id"] for s in secundarios]

            atd_ids = [r[0] for r in conn.execute(
                text("SELECT id FROM recepcao_atendimentos WHERE paciente_id = ANY(:ids)"),
                {"ids": ids_sec},
            ).all()]

            completar = {}
            for campo in _CAMPOS_COMPLETAR:
                if _vazio(principal[campo]):
                    for s in secundarios:
                        if not _vazio(s[campo]):
                            completar[campo] = s[campo]
                            break

            cns_de = None
            if not principal["cns"]:
                cns_de = next((s for s in secundarios if s["cns"]), None)

            print(
                f"{nome} | nasc {dtnasc}: principal id={principal['id']} <- {ids_sec}"
                f" | {len(atd_ids)} atendimento(s) movido(s)"
                f"{' | + CNS' if cns_de else ''}"
                f"{' | completa ' + ','.join(completar) if completar else ''}"
            )
            total_atd += len(atd_ids)
            backup["grupos"].append({
                "principal": _serializavel(principal),
                "secundarios": [_serializavel(s) for s in secundarios],
                "atendimentos_movidos": atd_ids,
                "campos_completados": list(completar),
                "cns_movido_de": cns_de["id"] if cns_de else None,
            })

            if not aplicar:
                continue

            if atd_ids:
                conn.execute(
                    text("UPDATE recepcao_atendimentos SET paciente_id = :p, updated_at = now() "
                         "WHERE id = ANY(:ids)"),
                    {"p": principal["id"], "ids": atd_ids},
                )
            if cns_de:
                conn.execute(text("UPDATE pacientes SET cns = NULL WHERE id = :id"), {"id": cns_de["id"]})
                completar["cns"] = cns_de["cns"]
            completar["sem_documento"] = not principal["num_cpf"]
            sets = ", ".join(f"{c} = :{c}" for c in completar)
            conn.execute(text(f"UPDATE pacientes SET {sets} WHERE id = :id"), {**completar, "id": principal["id"]})

            _log(conn, "paciente", principal["id"], ["mescla"] + [c for c in completar if c != "sem_documento"])
            for s in secundarios:
                campos = ["mescla_para_" + str(principal["id"])]
                if cns_de and s["id"] == cns_de["id"]:
                    campos.append("cns")
                _log(conn, "paciente", s["id"], campos)
            for a in atd_ids:
                _log(conn, "atendimento", a, ["paciente_id"])

        if aplicar and backup["grupos"]:
            pasta = Path(__file__).resolve().parent.parent / "backups_mescla"
            pasta.mkdir(exist_ok=True)
            arq = pasta / f"mescla_{datetime.now():%Y%m%d_%H%M%S}.json"
            arq.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nBackup salvo em {arq}")

        print(f"\n{len(mesclaveis)} grupo(s) mesclável(is), {total_atd} atendimento(s) a mover.")
        print(f"{len(conflitos)} grupo(s) com CPF/CNS conflitante -- NÃO mexidos:")
        for (nome, dtnasc), itens in conflitos:
            docs = "; ".join(
                f"id={i['id']} cpf={i['num_cpf'] or '-'} cns={i['cns'] or '-'} atd={i['atendimentos']}"
                for i in itens
            )
            print(f"   {nome} | nasc {dtnasc}: {docs}")

        if not aplicar:
            print("\nDRY-RUN: nada foi gravado. Rode com --aplicar pra gravar.")


def _log(conn, recurso: str, recurso_id: int, campos: list[str]) -> None:
    conn.execute(
        text("INSERT INTO logs_auditoria (usuario_id, usuario_username, acao, recurso, recurso_id, campos_alterados) "
             "VALUES (NULL, :u, 'atualizar', :r, :id, CAST(:c AS JSON))"),
        {"u": _USUARIO_LOG, "r": recurso, "id": recurso_id, "c": json.dumps(campos)},
    )


if __name__ == "__main__":
    main()
