"""
apagar_cadastros_mesclados.py
=============================
Apaga os cadastros SECUNDÁRIOS deixados por scripts/mesclar_pacientes_duplicados.py
-- só os que:
  - aparecem na auditoria como "mescla_para_<id>" (feitos pelo script), e
  - não têm NENHUM atendimento (checado de novo aqui, na hora de apagar).

Autorizado pelo Fabio em 23/09/2026. Não é regra geral: fora disso, paciente
nunca é apagado (só atendimento).

Salva backup JSON completo dos cadastros em backend/backups_mescla/ antes de
apagar, e registra "remover" em logs_auditoria. Tudo numa transação só.

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\apagar_cadastros_mesclados.py            # só mostra (dry-run)
    .venv\\Scripts\\python scripts\\apagar_cadastros_mesclados.py --aplicar  # apaga
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402

_USUARIO_LOG = "script:mesclar_duplicados"

_SQL = text("""
    SELECT p.*
    FROM pacientes p
    WHERE p.id IN (
        SELECT l.recurso_id FROM logs_auditoria l
        WHERE l.recurso = 'paciente' AND l.usuario_username = :u
          AND CAST(l.campos_alterados AS TEXT) LIKE '%mescla_para_%'
    )
      AND NOT EXISTS (SELECT 1 FROM recepcao_atendimentos a WHERE a.paciente_id = p.id)
    ORDER BY p.id
""")


def main() -> None:
    aplicar = "--aplicar" in sys.argv
    engine = create_engine(settings.database_url_sync)

    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(_SQL, {"u": _USUARIO_LOG}).mappings().all()]
        for r in rows:
            print(f"id={r['id']:<7} {r['nome']}  nasc {r['dtnasc']}")
        print(f"\n{len(rows)} cadastro(s) a apagar.")

        if not aplicar or not rows:
            if not aplicar:
                print("DRY-RUN: nada foi apagado. Rode com --aplicar pra apagar.")
            return

        pasta = Path(__file__).resolve().parent.parent / "backups_mescla"
        pasta.mkdir(exist_ok=True)
        arq = pasta / f"apagados_{datetime.now():%Y%m%d_%H%M%S}.json"
        arq.write_text(
            json.dumps(
                [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in rows],
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

        ids = [r["id"] for r in rows]
        # NOT EXISTS de novo: se alguém registrou atendimento nesse meio tempo, não apaga.
        apagados = conn.execute(
            text("DELETE FROM pacientes p WHERE p.id = ANY(:ids) "
                 "AND NOT EXISTS (SELECT 1 FROM recepcao_atendimentos a WHERE a.paciente_id = p.id) "
                 "RETURNING p.id"),
            {"ids": ids},
        ).scalars().all()
        for pid in apagados:
            conn.execute(
                text("INSERT INTO logs_auditoria (usuario_id, usuario_username, acao, recurso, recurso_id, campos_alterados) "
                     "VALUES (NULL, :u, 'remover', 'paciente', :id, CAST(:c AS JSON))"),
                {"u": _USUARIO_LOG, "id": pid, "c": json.dumps(["cadastro_duplicado_mesclado"])},
            )
        print(f"Backup salvo em {arq}")
        print(f"{len(apagados)} cadastro(s) apagado(s).")


if __name__ == "__main__":
    main()
