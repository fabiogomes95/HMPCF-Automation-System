"""Migração de pacientes PostgreSQL (servidor) → Firebird CADCNS (este notebook),
necessária pro BPA Magnético aceitar a importação. Portado sem mudança do
antigo app Flask."""
import json
import re
from datetime import date
from typing import Iterator

import bpa_gerador as bpa

from bpa_local import postgres
from bpa_local.cache import cache
from bpa_local.services import limpar


def _texto(valor, max_len=9999) -> str:
    return str(valor).strip().upper()[:max_len] if valor is not None else ""


def _sexo(valor) -> str:
    s = _texto(valor, 1)
    return s if s in ("M", "F") else "I"


def _dtnasc(valor) -> str | None:
    if not valor:
        return None
    v = re.sub(r"\D", "", str(valor))
    return v if len(v) == 8 else None


def _cns_valido(cns: str) -> bool:
    return len(cns) == 15


def _carregar_existentes_fb(cur) -> tuple[dict, set]:
    """Carrega todos os CNS/CPF já cadastrados no Firebird de uma vez (1 consulta),
    para checar existência em memória em vez de 1 SELECT por paciente (CADCNS não
    tem índice em NUM_CPF — em memória evita a varredura completa da tabela repetida
    milhares de vezes, sem precisar mexer no schema do banco).

    Retorna (por_cns, cpf_set):
      por_cns  — {CNS: (ID_CADCNS, NUM_CPF atual)}, para achar cadastros antigos
                 (só CNS, sem CPF) e completar o CPF sem duplicar o registro.
      cpf_set  — conjunto de CPFs já gravados em algum registro.
    """
    cur.execute("SELECT ID_CADCNS, CNS, NUM_CPF FROM CADCNS")
    por_cns: dict = {}
    cpf_set: set = set()
    for id_cadcns, cns, cpf in cur.fetchall():
        cns = (cns or "").strip()
        cpf = (cpf or "").strip()
        if cns:
            por_cns[cns] = (id_cadcns, cpf)
        if cpf:
            cpf_set.add(cpf)
    return por_cns, cpf_set


def _status_paciente(por_cns: dict, cpf_set: set, cns: str, cpf: str):
    """Decide o que fazer com um paciente do Postgres:
      "duplicata" — CPF já gravado em algum registro, nada a fazer.
      "atualizar" — já existe cadastro pelo CNS, mas sem CPF; (status, ID_CADCNS).
      "novo"      — não existe cadastro nenhum; precisa inserir.
    """
    if cpf in cpf_set:
        return ("duplicata", None)
    if cns and cns in por_cns:
        id_existente, cpf_atual = por_cns[cns]
        if not cpf_atual:
            return ("atualizar", id_existente)
        return ("duplicata", None)
    return ("novo", None)


_COLUNAS = [
    "ID_CADCNS", "CNS", "NUM_CPF", "NOME", "DTNASC", "SEXO", "RACA", "MAEPCN",
    "LOGPCN", "NUMPCN", "BAIRRO_PCNTE", "CEPPCN", "IBGE", "CO_LOGRAD",
    "ETNIA", "NACIONALIDADE", "DDTEL_PCNTE", "TEL_PCNTE",
]
_SQL_INSERT = f"INSERT INTO CADCNS ({', '.join(_COLUNAS)}) VALUES ({', '.join(['?'] * len(_COLUNAS))})"


def mes_padrao() -> str:
    return date.today().strftime("%Y%m")


def preview(d: dict) -> dict:
    mes = d.get("mes", mes_padrao())
    try:
        pg = postgres.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"PostgreSQL: {e}"}
    try:
        cur = pg.cursor()
        cur.execute(postgres.query_pacientes_mes(mes))
        rows = cur.fetchall()
        total = len(rows)

        validos = [r for r in rows if bpa.valida_cpf(limpar(r[1]))]
        cpf_invalido = total - len(validos)

        fb = bpa.conectar()
        fb_cur = fb.cursor()
        por_cns, cpf_set = _carregar_existentes_fb(fb_cur)
        fb.close()

        novos = atualizar = ja_existem = 0
        for r in validos:
            status, _ = _status_paciente(por_cns, cpf_set, limpar(r[0]), limpar(r[1]))
            if status == "novo":
                novos += 1
            elif status == "atualizar":
                atualizar += 1
            else:
                ja_existem += 1

        return {
            "ok": True, "total": total, "novos": novos, "atualizar": atualizar,
            "ja_existem": ja_existem, "cpf_invalido": cpf_invalido,
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}
    finally:
        pg.close()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream(mes: str) -> Iterator[str]:
    """Migração com progresso ao vivo (Server-Sent Events)."""
    try:
        pg = postgres.conectar()
    except Exception as e:
        yield _sse({"tipo": "erro", "msg": f"PostgreSQL indisponível: {e}"})
        return

    yield _sse({"tipo": "log", "msg": "Conectado ao PostgreSQL."})

    try:
        cur = pg.cursor()
        cur.execute(postgres.query_pacientes_mes(mes))
        rows = cur.fetchall()
    except Exception as e:
        yield _sse({"tipo": "erro", "msg": f"Consulta falhou: {e}"})
        pg.close()
        return

    total = len(rows)
    yield _sse({"tipo": "log", "msg": f"{total} paciente(s) com CPF no mês.", "total": total})

    if total == 0:
        yield _sse({
            "tipo": "fim", "inseridos": 0, "atualizados": 0, "duplicatas": 0,
            "erros": 0, "cpf_invalidos": 0,
        })
        pg.close()
        return

    try:
        fb = bpa.conectar()
        fb_cur = fb.cursor()
    except Exception as e:
        yield _sse({"tipo": "erro", "msg": f"Firebird indisponível: {e}"})
        pg.close()
        return

    yield _sse({"tipo": "log", "msg": "Conectado ao Firebird."})

    fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
    max_id = fb_cur.fetchone()[0] or 0

    por_cns, cpf_set = _carregar_existentes_fb(fb_cur)
    yield _sse({"tipo": "log", "msg": f"{len(cpf_set)} CPF(s) já cadastrados carregados em memória."})

    inseridos = atualizados = duplicatas = erros = cpf_invalidos = 0
    LOTE = 50

    for i, row in enumerate(rows, 1):
        cns_r, cpf_r, nome_r, dn_r, sexo_r, raca_r, mae_r, \
            log_r, num_r, bairro_r, cep_r, ibge_r, nac_r, ddd_r, tel_r = row
        cns = limpar(cns_r)
        cpf = limpar(cpf_r)

        if not bpa.valida_cpf(cpf):
            cpf_invalidos += 1
            yield _sse({"tipo": "log", "msg": f"CPF ausente/inválido, paciente pulado: {nome_r} ({cpf_r!r})"})
            continue

        if cns and not _cns_valido(cns):
            cns = ""  # CNS não é mais obrigatório — descarta se mal formatado, mas mantém o CPF

        status, id_existente = _status_paciente(por_cns, cpf_set, cns, cpf)

        if status == "duplicata":
            duplicatas += 1

        elif status == "atualizar":
            try:
                fb_cur.execute("UPDATE CADCNS SET NUM_CPF = ? WHERE ID_CADCNS = ?", [cpf, id_existente])
                atualizados += 1
                cpf_set.add(cpf)
                por_cns[cns] = (id_existente, cpf)
            except Exception as e:
                erros += 1
                yield _sse({"tipo": "log", "msg": f"Erro ao atualizar CPF de {nome_r} (CNS {cns}): {e}"})

        else:  # "novo"
            max_id += 1
            try:
                # SUS deixado de lado a partir de 10/07/2026 (decisão do
                # usuário) — cadastro novo migra CPF e todos os outros dados
                # normalmente, mas nunca grava o CNS vindo do Postgres. O CNS
                # acima (`cns`) continua sendo usado só pra achar cadastro
                # EXISTENTE no Firebird e completar o CPF nele (branch
                # "atualizar"), nunca para popular um cadastro novo.
                fb_cur.execute(_SQL_INSERT, [
                    max_id, "", cpf,
                    _texto(nome_r, 30) or "SEM NOME",
                    _dtnasc(dn_r),
                    _sexo(sexo_r),
                    _texto(raca_r, 2) or "03",
                    _texto(mae_r, 30),
                    _texto(log_r, 30) or "PRINCIPAL",
                    _texto(num_r, 5) or "S/N",
                    _texto(bairro_r, 30) or "CENTRO",
                    limpar(cep_r)[:8] or "59575000",
                    limpar(ibge_r)[:6] or "240360",
                    "081", "",
                    _texto(nac_r, 3) or "010",
                    _texto(ddd_r, 2),
                    _texto(tel_r, 9),
                ])
                inseridos += 1
                # Atualiza o cache em memória — sem isso, dois registros do mesmo
                # paciente no mesmo lote (ex: endereço mudou entre atendimentos)
                # seriam inseridos duas vezes no Firebird. Cadastro novo não
                # grava CNS (ver acima), então só o CPF entra no cache.
                cpf_set.add(cpf)
            except Exception as e:
                erros += 1
                yield _sse({"tipo": "log", "msg": f"Erro CPF {cpf}: {e}"})

        if i % LOTE == 0:
            fb.commit()
            yield _sse({
                "tipo": "progresso",
                "msg": f"{i}/{total} — inseridos: {inseridos} | atualizados: {atualizados} | duplicatas: {duplicatas}",
                "i": i, "total": total,
                "inseridos": inseridos, "atualizados": atualizados, "duplicatas": duplicatas,
            })

    try:
        fb.commit()
    except Exception as e:
        yield _sse({"tipo": "log", "msg": f"Erro no commit: {e}"})

    fb.close()
    pg.close()
    cache.carregar_pacientes()

    yield _sse({
        "tipo": "fim",
        "msg": f"Concluído! Inseridos: {inseridos} | Atualizados (CPF): {atualizados} | "
               f"Duplicatas: {duplicatas} | CPF inválido: {cpf_invalidos} | Erros: {erros}",
        "inseridos": inseridos, "atualizados": atualizados, "duplicatas": duplicatas, "erros": erros,
        "cpf_invalidos": cpf_invalidos,
    })
