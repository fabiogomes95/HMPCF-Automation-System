"""Migração de pacientes PostgreSQL (servidor) → Firebird CADCNS (este notebook),
necessária pro BPA Magnético aceitar a importação. Portado sem mudança do
antigo app Flask."""
import json
import re
import threading
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


def chave_nome_nasc(nome, dtnasc) -> tuple[str, str]:
    """Identidade de paciente SEM CPF: nome (como vai pro Firebird, 30 letras) + nascimento."""
    return (re.sub(r"\s+", " ", str(nome or "").strip().upper())[:30].strip(), _dtnasc(dtnasc) or "")


def _carregar_existentes_fb(cur) -> tuple[set, set]:
    """Carrega de uma vez (1 consulta) o que já está no Firebird, pra checar em
    memória em vez de 1 SELECT por paciente (CADCNS não tem índice em NUM_CPF).

    Retorna (cpf_set, nome_nasc):
      cpf_set   — CPFs já gravados.
      nome_nasc — (nome, nascimento) de todos os cadastros: paciente SEM CPF
                  só entra se ninguém com o mesmo nome e nascimento existir.

    Desde 24/09/2026 não existe mais "completar CPF" em cadastro antigo só com
    SUS: o Firebird foi migrado de novo só com CPF (ninguém tem SUS lá)."""
    cur.execute("SELECT NUM_CPF, NOME, DTNASC FROM CADCNS")
    cpf_set: set = set()
    nome_nasc: set = set()
    for cpf, nome, dtnasc in cur.fetchall():
        nome_nasc.add(chave_nome_nasc(nome, dtnasc))
        cpf = (cpf or "").strip()
        if cpf:
            cpf_set.add(cpf)
    return cpf_set, nome_nasc


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

        sem_doc = [r for r in rows if not limpar(r[1])]
        validos = [r for r in rows if bpa.valida_cpf(limpar(r[1]))]
        cpf_invalido = total - len(validos) - len(sem_doc)

        fb = bpa.conectar()
        fb_cur = fb.cursor()
        cpf_set, nome_nasc = _carregar_existentes_fb(fb_cur)
        fb.close()

        novos = ja_existem = novos_sem_doc = 0
        for r in sem_doc:
            if chave_nome_nasc(r[2], r[3]) in nome_nasc:
                ja_existem += 1
            elif _dtnasc(r[3]) and str(r[2] or "").strip():
                novos_sem_doc += 1
        for r in validos:
            if limpar(r[1]) in cpf_set:
                ja_existem += 1
            else:
                novos += 1

        return {
            "ok": True, "total": total, "novos": novos + novos_sem_doc,
            "ja_existem": ja_existem, "cpf_invalido": cpf_invalido, "sem_documento": novos_sem_doc,
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}
    finally:
        pg.close()




# Uma migração por vez (manual ou automática): as duas numeram cadastro novo
# com MAX(ID_CADCNS)+1 -- rodando juntas repetiriam o mesmo ID.
TRAVA = threading.Lock()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream(mes: str) -> Iterator[str]:
    """Migração manual de uma competência, com progresso ao vivo (Server-Sent Events)."""
    if not TRAVA.acquire(blocking=False):
        yield _sse({"tipo": "erro", "msg": "Já existe uma migração em andamento (a automática do dia). Aguarde terminar."})
        return
    try:
        for evento in migrar(postgres.query_pacientes_mes(mes)):
            yield _sse(evento)
    finally:
        TRAVA.release()


def migrar(query: str) -> Iterator[dict]:
    """Núcleo da migração (manual e automática): gera eventos
    {"tipo": log | progresso | erro | fim, ...}. Quem chama segura a TRAVA."""
    try:
        pg = postgres.conectar()
    except Exception as e:
        yield {"tipo": "erro", "msg": f"PostgreSQL indisponível: {e}"}
        return

    yield {"tipo": "log", "msg": "Conectado ao PostgreSQL."}

    try:
        cur = pg.cursor()
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        yield {"tipo": "erro", "msg": f"Consulta falhou: {e}"}
        pg.close()
        return

    total = len(rows)
    yield {"tipo": "log", "msg": f"{total} paciente(s) atendido(s) no período.", "total": total}

    if total == 0:
        yield {
            "tipo": "fim", "inseridos": 0, "duplicatas": 0,
            "erros": 0, "cpf_invalidos": 0, "sem_documento": 0,
        }
        pg.close()
        return

    try:
        fb = bpa.conectar()
        fb_cur = fb.cursor()
    except Exception as e:
        yield {"tipo": "erro", "msg": f"Firebird indisponível: {e}"}
        pg.close()
        return

    yield {"tipo": "log", "msg": "Conectado ao Firebird."}

    fb_cur.execute("SELECT MAX(ID_CADCNS) FROM CADCNS")
    max_id = fb_cur.fetchone()[0] or 0

    cpf_set, nome_nasc = _carregar_existentes_fb(fb_cur)
    yield {"tipo": "log", "msg": f"{len(cpf_set)} CPF(s) já cadastrados carregados em memória."}

    inseridos = duplicatas = erros = cpf_invalidos = sem_documento = 0
    LOTE = 50

    for i, row in enumerate(rows, 1):
        cns_r, cpf_r, nome_r, dn_r, sexo_r, raca_r, mae_r, \
            log_r, num_r, bairro_r, cep_r, ibge_r, nac_r, ddd_r, tel_r = row
        cpf = limpar(cpf_r)

        if not cpf:
            # Paciente SEM documento (cadastrado sem CPF na recepção): entra sem
            # CPF e sem CNS -- no BPA-I sai com prd_possui_cpf_cns = "s".
            chave = chave_nome_nasc(nome_r, dn_r)
            if not chave[0] or not chave[1]:
                erros += 1
                yield {"tipo": "log", "msg": f"Sem CPF e sem nome/nascimento completos, pulado: {nome_r!r}"}
            elif chave in nome_nasc:
                duplicatas += 1
            else:
                max_id += 1
                try:
                    fb_cur.execute(_SQL_INSERT, [
                        max_id, "", "",
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
                    sem_documento += 1
                    nome_nasc.add(chave)
                except Exception as e:
                    erros += 1
                    yield {"tipo": "log", "msg": f"Erro ao inserir {nome_r} (sem CPF): {e}"}
            if i % LOTE == 0:
                fb.commit()
            continue

        if not bpa.valida_cpf(cpf):
            cpf_invalidos += 1
            yield {"tipo": "log", "msg": f"CPF ausente/inválido, paciente pulado: {nome_r} ({cpf_r!r})"}
            continue

        if cpf in cpf_set:
            duplicatas += 1

        else:  # novo
            max_id += 1
            try:
                # SUS deixado de lado a partir de 10/07/2026 (decisão do
                # usuário) — cadastro novo migra CPF e todos os outros dados
                # normalmente, mas nunca grava o CNS vindo do Postgres.
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
                nome_nasc.add(chave_nome_nasc(nome_r, dn_r))
            except Exception as e:
                erros += 1
                yield {"tipo": "log", "msg": f"Erro CPF {cpf}: {e}"}

        if i % LOTE == 0:
            fb.commit()
            yield {
                "tipo": "progresso",
                "msg": f"{i}/{total} — inseridos: {inseridos} | duplicatas: {duplicatas}",
                "i": i, "total": total,
                "inseridos": inseridos, "duplicatas": duplicatas,
            }

    try:
        fb.commit()
    except Exception as e:
        yield {"tipo": "log", "msg": f"Erro no commit: {e}"}

    fb.close()
    pg.close()
    cache.carregar_pacientes()

    yield {
        "tipo": "fim",
        "msg": f"Concluído! Inseridos: {inseridos} (sem CPF: {sem_documento}) | "
               f"Duplicatas: {duplicatas} | CPF inválido: {cpf_invalidos} | Erros: {erros}",
        "inseridos": inseridos, "duplicatas": duplicatas, "erros": erros,
        "cpf_invalidos": cpf_invalidos, "sem_documento": sem_documento,
    }
