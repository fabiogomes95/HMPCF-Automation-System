"""Nutrição: lê a planilha do mês (DADOS NUTRIÇÃO.xlsx), acha cada paciente
no Firebird e gera UM arquivo BPA-I com as nutricionistas e todos os dias
(BPA_NUTRICAO_<AAAAMM>.txt), pra importar no BPA Magnético.

Não usa nem escreve os lotes DD-MM-AAAA.txt da digitação: a planilha é o
lote da nutrição. A leitura da planilha está em bpa/nutricao.py."""
import base64
import os
from datetime import datetime

import bpa_gerador as bpa
import nutricao as planilha

from bpa_local.cache import cache


def _xlsx(d: dict) -> bytes:
    try:
        return base64.b64decode(d.get("arquivo_b64") or "", validate=True)
    except Exception:
        raise ValueError("Arquivo inválido — escolha a planilha .xlsx de novo.")


def carregar_nutricionistas(con) -> list[dict]:
    """Profissionais com CBO de nutricionista (223710) no CADMED_CBO_CNES."""
    cur = con.cursor()
    cur.execute(
        "SELECT M.CADMED_CNS, M.CADMED_NOME FROM CADMED M "
        "WHERE M.CADMED_CNS IN (SELECT C.MED_CNS FROM CADMED_CBO_CNES C WHERE C.MED_CBO = ?) "
        "ORDER BY M.CADMED_NOME",
        (planilha.CBO_NUTRI,),
    )
    return [{"cns": str(cns).strip(), "nome": str(nome).strip().upper()} for cns, nome in cur.fetchall()]


class _Indice:
    """Pacientes do cache do Firebird por CPF, por nome+nascimento e por nome."""

    def __init__(self, pacientes: list[dict]) -> None:
        self.por_cpf: dict[str, dict] = {}
        self.por_nome_nasc: dict[tuple, list[dict]] = {}
        self.por_nome: dict[str, list[dict]] = {}
        for p in pacientes:
            if p["cpf"]:
                self.por_cpf.setdefault(p["cpf"], p)
            nome = planilha.normalizar_nome(p["nome"])
            self.por_nome_nasc.setdefault((nome, p["dtnasc"]), []).append(p)
            self.por_nome.setdefault(nome, []).append(p)

    def resolver(self, pac: dict) -> dict:
        """Acha o paciente da planilha no Firebird. Situações:
        ok        — CPF da planilha está no Firebird
        corrigido — CPF errado/vazio, achado por nome+nascimento (ou só pelo nome, se único)
        sem_doc   — achado, mas não tem CPF no Firebird: vai como "sem documento"
        nao_achado — não está no Firebird (migre o paciente e leia de novo)"""
        cpf = pac["cpf"]
        if len(cpf) == 11 and cpf in self.por_cpf:
            return self._achado(self.por_cpf[cpf], "ok")

        nome = planilha.normalizar_nome(pac["nome"])
        candidatos = self.por_nome_nasc.get((nome, pac["nascimento"])) or []
        motivo = "nome e nascimento"
        if len(candidatos) != 1:
            so_nome = self.por_nome.get(nome) or []
            if not candidatos and len(so_nome) == 1:
                candidatos, motivo = so_nome, "nome (nascimento diferente)"
        if len(candidatos) == 1:
            p = candidatos[0]
            if not p["cpf"]:
                return self._achado(p, "sem_doc", motivo)
            return self._achado(p, "corrigido", motivo)
        return {"situacao": "nao_achado", "doc": "", "nome_bpa": "", "cpf_bpa": "",
                "motivo": "mais de um paciente com esse nome" if candidatos else ""}

    @staticmethod
    def _achado(p: dict, situacao: str, motivo: str = "") -> dict:
        doc = p["cpf"] if p["cpf"] else bpa.doc_por_id(p["id"])
        return {"situacao": situacao, "doc": doc, "nome_bpa": p["nome"], "cpf_bpa": p["cpf"], "motivo": motivo}


def ler(d: dict) -> dict:
    """Sem `aba`: devolve só as abas da planilha. Com `aba`: os dias, a
    nutricionista de cada dia e cada paciente já procurado no Firebird."""
    try:
        conteudo = _xlsx(d)
        abas = planilha.listar_abas(conteudo)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    except Exception:
        return {"ok": False, "erro": "Não consegui abrir a planilha — confira se é o .xlsx da nutrição."}
    if not abas:
        return {"ok": False, "erro": "Nenhuma aba de mês (ex. AGO-26) nessa planilha."}

    aba = (d.get("aba") or "").strip()
    if not aba:
        return {"ok": True, "abas": abas}
    if aba not in abas:
        return {"ok": False, "erro": f"A planilha não tem a aba '{aba}'."}

    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}
    try:
        nutris = carregar_nutricionistas(con)
    finally:
        con.close()
    if not nutris:
        return {"ok": False, "erro": "Nenhuma nutricionista (CBO 223710) cadastrada no BPA Magnético."}

    # Mesmo nome curto (1º nome) que se escreve na planilha
    for n in nutris:
        n["curto"] = n["nome"].split()[0]
    lido = planilha.ler_aba(conteudo, aba, nutris)

    indice = _Indice(cache.pacientes)
    contagem = {"ok": 0, "corrigido": 0, "sem_doc": 0, "nao_achado": 0}
    dias = []
    for dia in lido["dias"]:
        pacientes = []
        for p in dia["pacientes"]:
            r = indice.resolver(p)
            contagem[r["situacao"]] += 1
            pacientes.append({**p, **r})
        dias.append({
            "data": dia["data"].strftime("%d/%m/%Y") if dia["data"] else "",
            "nutricionistas": [n["cns"] for n in dia["nutricionistas"]],
            "pacientes": pacientes,
        })

    return {
        "ok": True, "abas": abas, "aba": aba,
        "competencia": lido["competencia"],
        "nutricionistas": [{"cns": n["cns"], "nome": n["nome"], "curto": n["curto"]} for n in nutris],
        "dias": dias, "avisos": lido["avisos"], "contagem": contagem,
    }


def _producao_fora_das_datas(con, cns_prof: str, competencia: str, datas: list[str]) -> tuple[int, int]:
    """(atendimentos da nutricionista no mês FORA das datas do arquivo — a
    folha/sequência continua depois deles; atendimentos JÁ importados nessas
    datas — importar de novo duplicaria)."""
    cur = con.cursor()
    cur.execute("SELECT PRD_DTATEN FROM S_PRD WHERE PRD_CNSMED = ? AND PRD_CMP = ?", (cns_prof, competencia))
    fora = dentro = 0
    conjunto = set(datas)
    for (dt,) in cur.fetchall():
        if str(dt).strip() in conjunto:
            dentro += 1
        else:
            fora += 1
    return fora, dentro


def gerar(d: dict) -> dict:
    """Recebe o que a tela confirmou — [{data, nutricionistas:[cns], docs:[...]}]
    — e grava BPA_NUTRICAO_<AAAAMM>.txt. Dia com mais de uma nutricionista
    tem os pacientes divididos igualmente entre elas."""
    competencia = (d.get("competencia") or "").strip()
    if len(competencia) != 6 or not competencia.isdigit():
        return {"ok": False, "erro": "Competência inválida."}

    # cns -> {AAAAMMDD: [docs]}
    por_nutri: dict[str, dict[str, list[str]]] = {}
    for dia in d.get("dias") or []:
        try:
            dt = datetime.strptime((dia.get("data") or "").strip(), "%d/%m/%Y").date()
        except ValueError:
            return {"ok": False, "erro": f"Data inválida: '{dia.get('data')}'."}
        if dt.strftime("%Y%m") != competencia:
            return {"ok": False, "erro": f"{dt:%d/%m/%Y} não é do mês da planilha."}
        nutris = [{"cns": c} for c in dia.get("nutricionistas") or []]
        docs = [x for x in dia.get("docs") or [] if x]
        if not docs:
            continue
        if not nutris:
            return {"ok": False, "erro": f"Escolha a nutricionista do dia {dt:%d/%m/%Y}."}
        for cns, lista in planilha.dividir(docs, nutris).items():
            por_nutri.setdefault(cns, {}).setdefault(dt.strftime("%Y%m%d"), []).extend(lista)
    if not por_nutri:
        return {"ok": False, "erro": "Nenhum paciente para gerar."}

    try:
        con = bpa.conectar()
    except Exception as e:
        return {"ok": False, "erro": f"Firebird indisponível: {e}"}

    try:
        nomes = {n["cns"]: n["nome"] for n in carregar_nutricionistas(con)}
        linhas: list[str] = []
        n_folhas = 0
        resumo = []
        nao_encontrados: list[str] = []
        for cns_raw, por_data in sorted(por_nutri.items(), key=lambda x: nomes.get(x[0], x[0])):
            if cns_raw not in nomes:
                return {"ok": False, "erro": f"Profissional {cns_raw} não é nutricionista no BPA Magnético."}
            cns_prof = cns_raw.zfill(15)
            datas = sorted(por_data)
            fora, ja_importados = _producao_fora_das_datas(con, cns_prof, competencia, datas)
            # Folha/sequência continuam da produção que ela já tem no mês
            # (99 por folha), atravessando os dias do arquivo sem recomeçar.
            qtd = 0
            for data_aten in datas:
                pacientes, nao_enc, _ = bpa.buscar_pacientes(con, por_data[data_aten])
                nao_encontrados.extend(nao_enc)
                if not pacientes:
                    continue
                feitos = fora + qtd
                novas, _ = bpa.montar_linhas(
                    pacientes, planilha.CODIGO_NUTRI, planilha.CBO_NUTRI, cns_prof,
                    data_aten, competencia, feitos // 99 + 1, feitos % 99 + 1,
                )
                linhas.extend(novas)
                qtd += len(novas)
            if qtd:
                n_folhas += (fora + qtd - 1) // 99 - fora // 99 + 1
                resumo.append({"nome": nomes[cns_raw], "atendimentos": qtd, "dias": len(datas),
                               "ja_importados": ja_importados})

        if not linhas:
            return {"ok": False, "erro": "Nenhum paciente encontrado no Firebird."}

        nome_arquivo = f"BPA_NUTRICAO_{competencia}.txt"
        pasta = bpa.BPA_LOTES_DIR
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, nome_arquivo)
        cabecalho = bpa.montar_cabecalho(competencia, len(linhas), n_folhas, linhas)
        try:
            with open(caminho, "w", encoding="latin-1", newline="") as f:
                f.write(cabecalho + "\r\n")
                for linha in linhas:
                    f.write(linha + "\r\n")
        except PermissionError:
            return {"ok": False, "erro": (
                f"Não consegui salvar {nome_arquivo}: o arquivo está aberto em outro programa "
                "(BPA Magnético, Bloco de Notas ou Excel). Feche-o e clique em gerar de novo."
            )}

        return {
            "ok": True, "arquivo": nome_arquivo, "caminho": caminho,
            "registros": len(linhas), "folhas": n_folhas,
            "competencia": f"{competencia[4:]}/{competencia[:4]}",
            "nutricionistas": resumo, "nao_encontrados": nao_encontrados,
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}
    finally:
        con.close()
