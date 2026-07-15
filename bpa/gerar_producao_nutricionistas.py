"""
Importa a produção de nutricionistas (BPA-I, CBO 223710) a partir da planilha
"DADOS PACIENTES.xlsx" (Downloads) e gera, em C:\\BPA\\bpa_lotes, DOIS ARQUIVOS
PRÓPRIOS da nutrição — nomes exclusivos, NUNCA reaproveita/edita os arquivos
DD-MM-AAAA.txt já usados por médico/enfermeiro (isso já foi tentado uma vez e
revertido a pedido do usuário em 2026-07-15 — ver histórico da conversa):

  1. NUTRICAO_<competencia>.txt — um único arquivo com todos os blocos
     "PROFISSIONAL: ... | CNS: ... | DATA: ..." + CPFs do mês inteiro,
     separados por data e profissional dentro do mesmo arquivo.
  2. BPA_NUTRICIONISTAS_<competencia>.txt — arquivo final BPA-I (350 chars/
     linha, layout DATASUS), mesma lógica de folha/sequência que o botão
     "Gerar BPA-I" do Flask usa pra médico/enfermeiro, só que rodando o mês
     inteiro de uma vez (pra não colidir folha/sequência entre dias fora de
     ordem). Nome propositalmente diferente de BPAI_<cnes>_<competencia>.txt
     (esse é o export oficial médico/enfermeiro em C:\\BPA — não confundir).

Este script é 100% standalone: nunca chama bpa.criar_cabecalho_lote,
bpa.adicionar_documento_lote, bpa.regravar_lote nem qualquer outra função que
mexa nos lotes diários compartilhados.

Uso:
    python gerar_producao_nutricionistas.py

Regras de leitura da planilha (coluna A mistura data / nome da nutricionista /
anotações, coluna D é o CPF do paciente — confirmado com o usuário em
2026-07-15):
  - Nome da nutricionista, uma vez escrito, vale para as linhas seguintes até
    aparecer um nome novo (inclusive atravessando dias sem nome novo escrito).
  - "FDS" é só anotação de fim de semana — ignorada, não muda nada.
  - "TODAS NUT" (todas as 3 nutricionistas naquele dia) é atribuída a só 1
    delas, em rodízio entre as 3, por decisão do usuário.
  - CPFs repetidos em dias diferentes são normais (pacientes internados com
    dieta todos os dias) — não é deduplicado entre dias, só duplicata
    consecutiva dentro do mesmo bloco (mesma regra do resto do sistema).
"""
from __future__ import annotations

import itertools
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpa_gerador as bpa  # noqa: E402

PLANILHA    = Path.home() / "Downloads" / "DADOS PACIENTES.xlsx"
ABA         = "JUN -26"
ANO, MES    = 2026, 6
COMPETENCIA = f"{ANO}{MES:02d}"

# Nutricionista ainda NAO esta cadastrada em bpa_gerador.PROCEDIMENTOS (essa
# integracao no Flask fica pra depois -- ver NUTRICIONISTAS_TODO.md). Este
# script e 100% standalone: define seus proprios codigo/cbo e usa só as
# funcoes genericas de bpa_gerador (nao dependem de categoria pré-cadastrada).
CBO_NUTRI      = "223710"
CODIGO_NUTRI   = "0301010048"  # mesmo codigo usado para enfermeiro

# Nomes de arquivo EXCLUSIVOS da nutricao -- nunca DD-MM-AAAA.txt (esses sao
# dos lotes compartilhados de medico/enfermeiro) nem BPAI_<cnes>_<comp>.txt
# (esse e' o export oficial medico/enfermeiro).
ARQUIVO_LOTE_NUTRICAO = f"NUTRICAO_{COMPETENCIA}.txt"
ARQUIVO_BPAI_NUTRICAO = f"BPA_NUTRICIONISTAS_{COMPETENCIA}.txt"


def carregar_nutricionistas() -> dict[str, dict]:
    """{'BA': {'cns':..., 'nome':...}, 'MA': {...}, 'NA': {...}} a partir do
    Firebird (CADMED_CBO_CNES + CADMED), chaveado pelas 2 primeiras letras do
    nome cadastrado — discrimina bem os 3 nomes reais (Barbara/Mariane/Nailla)
    mesmo com erro de digitação no resto do nome na planilha."""
    con = bpa.conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT MED_CNS FROM CADMED_CBO_CNES WHERE MED_CBO = ?", (CBO_NUTRI,))
        cns_list = [str(r[0]).strip() for r in cur.fetchall()]
        resultado = {}
        for cns in cns_list:
            cur.execute("SELECT CADMED_NOME FROM CADMED WHERE CADMED_CNS = ?", (cns,))
            row = cur.fetchone()
            nome = str(row[0]).strip() if row else ""
            prefixo = nome.upper()[:2]
            resultado[prefixo] = {"cns": cns, "nome": nome}
        return resultado
    finally:
        con.close()


def classificar_celula_a(val, nutris: dict[str, dict]) -> tuple[str, object]:
    if pd.isna(val):
        return "vazio", None
    if isinstance(val, (pd.Timestamp, datetime, date)):
        d = val.date() if isinstance(val, (pd.Timestamp, datetime)) else val
        return "data", d
    s = str(val).strip()
    if not s:
        return "vazio", None
    su = s.upper()
    if su == "FDS":
        return "nota", None
    if su.startswith("TODAS"):
        return "todas_nut", None
    letras = "".join(c for c in su if c.isalpha())
    if letras[:2] in nutris:
        return "nutri", letras[:2]
    m = re.match(r"\s*(\d{1,2})", s)
    if m:
        try:
            return "data", date(ANO, MES, int(m.group(1)))
        except ValueError:
            pass
    return "desconhecido", s


def limpar_cpf(valor) -> str:
    if pd.isna(valor):
        return ""
    if isinstance(valor, (int, float)):
        s = str(int(valor))
    else:
        s = re.sub(r"\D", "", str(valor))
    if len(s) == 10:
        s = s.zfill(11)
    return s


def extrair_registros(nutris: dict[str, dict]) -> tuple[list[dict], list[tuple]]:
    df = pd.read_excel(PLANILHA, sheet_name=ABA, header=None)

    registros: list[dict] = []
    desconhecidos: list[tuple] = []
    current_date: date | None = None
    current_nutri: str | None = None
    rotacao_todas = itertools.cycle(sorted(nutris))

    for idx in range(3, len(df)):
        row = df.iloc[idx]
        tipo, val = classificar_celula_a(row[0], nutris)

        if tipo == "data":
            current_date = val
        elif tipo == "nutri":
            current_nutri = val
        elif tipo == "todas_nut":
            current_nutri = next(rotacao_todas)
        elif tipo == "desconhecido":
            desconhecidos.append((idx + 1, val))
        # 'vazio' e 'nota' (FDS) nao mudam o estado

        nome_pac = row[1]
        cpf_raw  = row[3]
        if pd.isna(nome_pac) and pd.isna(cpf_raw):
            continue  # linha separadora em branco

        if current_date is None:
            desconhecidos.append((idx + 1, "linha de paciente antes de qualquer data"))
            continue

        registros.append({
            "linha_excel": idx + 1,
            "data": current_date,
            "nutri_prefixo": current_nutri,
            "nome_pac": "" if pd.isna(nome_pac) else str(nome_pac).strip(),
            "cpf": limpar_cpf(cpf_raw),
        })

    primeiro_nutri = next((r["nutri_prefixo"] for r in registros if r["nutri_prefixo"]), None)
    for r in registros:
        if r["nutri_prefixo"] is None:
            r["nutri_prefixo"] = primeiro_nutri

    return registros, desconhecidos


def agrupar_por_nutri_dia(registros: list[dict]) -> dict[str, dict[date, list[str]]]:
    por_nutri: dict[str, dict[date, list[str]]] = {}
    for r in registros:
        if not r["cpf"]:
            continue
        dias = por_nutri.setdefault(r["nutri_prefixo"], {})
        cpfs = dias.setdefault(r["data"], [])
        if not cpfs or cpfs[-1] != r["cpf"]:
            cpfs.append(r["cpf"])
    return por_nutri


def gravar_lote_nutricao(por_nutri: dict[str, dict[date, list[str]]], nutris: dict[str, dict]) -> str:
    """Escreve UM único arquivo (ARQUIVO_LOTE_NUTRICAO), com um bloco
    "PROFISSIONAL: ... | CNS: ... | DATA: ..." por (nutricionista, dia),
    sempre reescrito do zero a partir da planilha — não mexe em nenhum outro
    arquivo do bpa_lotes."""
    caminho = os.path.join(bpa.BPA_LOTES_DIR, ARQUIVO_LOTE_NUTRICAO)
    with open(caminho, "w", encoding="utf-8") as f:
        for prefixo, dias in por_nutri.items():
            info = nutris[prefixo]
            for d in sorted(dias):
                cpfs = dias[d]
                if not cpfs:
                    continue
                data_br = d.strftime("%d/%m/%Y")
                f.write(f"PROFISSIONAL: {info['nome'].upper()} | CNS: {info['cns']} | DATA: {data_br}\n")
                for cpf in cpfs:
                    f.write(f"{cpf}\n")
    return caminho


def gerar_bpai(por_nutri: dict[str, dict[date, list[str]]], nutris: dict[str, dict]):
    con = bpa.conectar()
    try:
        # so 11 digitos passa pro Firebird (NUM_CPF e' de largura fixa -- um
        # CPF malformado de 12+ digitos vindo da planilha estoura a coluna e
        # derruba a query inteira com "string truncation"). O que ficar de
        # fora aqui sobra em `cpfs_invalidos` mais abaixo, no loop principal.
        todos_cpfs = sorted({
            c for dias in por_nutri.values() for cpfs in dias.values() for c in cpfs
            if len(c) == 11
        })
        pac_por_cpf = bpa._buscar_dados_pacientes(con, [], todos_cpfs)
    finally:
        con.close()

    proc = CODIGO_NUTRI
    cbo  = CBO_NUTRI

    todas_linhas: list[str] = []
    n_folhas_total = 0
    resumo = []
    nao_encontrados: set[str] = set()
    cpfs_invalidos: set[str] = set()

    for prefixo, dias in por_nutri.items():
        info = nutris[prefixo]
        cns_prof = info["cns"]
        producao_anterior = 0
        for d in sorted(dias):
            cpfs = dias[d]
            pacientes = []
            for cpf in cpfs:
                if len(cpf) != 11 or not bpa.valida_cpf(cpf):
                    cpfs_invalidos.add(cpf)
                    continue
                pac = pac_por_cpf.get(cpf)
                if pac:
                    pacientes.append(pac)
                else:
                    nao_encontrados.add(cpf)
            if not pacientes:
                continue

            data_aten = d.strftime("%Y%m%d")
            folha_ini = producao_anterior // 99 + 1
            seq_ini   = producao_anterior % 99 + 1
            linhas, folha_fim = bpa.montar_linhas(
                pacientes, proc, cbo, cns_prof, data_aten, COMPETENCIA, folha_ini, seq_ini
            )
            todas_linhas.extend(linhas)
            n_folhas_total += folha_fim - folha_ini + 1
            producao_anterior += len(pacientes)
            resumo.append((info["nome"], d, len(pacientes), folha_ini, seq_ini, folha_fim))

    if not todas_linhas:
        return None, resumo, nao_encontrados, cpfs_invalidos

    ok, tam = bpa.validar(todas_linhas)
    if not ok:
        raise RuntimeError("Linhas do BPA-I com tamanho inconsistente — abortando geração.")

    cabecalho = bpa.montar_cabecalho(COMPETENCIA, len(todas_linhas), n_folhas_total, todas_linhas)
    caminho   = os.path.join(bpa.BPA_LOTES_DIR, ARQUIVO_BPAI_NUTRICAO)
    # newline="" garante CRLF real sem duplicação (mesma técnica de bpa.gerar_arquivo)
    with open(caminho, "w", encoding="latin-1", newline="") as f:
        f.write(cabecalho + "\r\n")
        for linha in todas_linhas:
            f.write(linha + "\r\n")
    return caminho, resumo, nao_encontrados, cpfs_invalidos


def main():
    print(f"Lendo {PLANILHA} — aba '{ABA}'...")
    nutris = carregar_nutricionistas()
    if len(nutris) != 3:
        print(f"AVISO: esperava 3 nutricionistas com CBO {CBO_NUTRI}, achei {len(nutris)}: {nutris}")

    registros, desconhecidos = extrair_registros(nutris)
    print(f"{len(registros)} linha(s) de paciente extraída(s) da planilha.")

    por_nutri = agrupar_por_nutri_dia(registros)

    print("\n== Gravando lote da nutrição em", bpa.BPA_LOTES_DIR, "==")
    caminho_lote = gravar_lote_nutricao(por_nutri, nutris)
    print(f"  {caminho_lote}")

    print("\n== Gerando arquivo BPA-I da competência", COMPETENCIA, "==")
    caminho, resumo, nao_encontrados, cpfs_invalidos = gerar_bpai(por_nutri, nutris)

    print("\n== Resumo por nutricionista/dia ==")
    for nome, d, qtd, f_ini, s_ini, f_fim in resumo:
        print(f"  {d.strftime('%d/%m')} — {nome}: {qtd} atendimento(s), folha {f_ini}/seq {s_ini} até folha {f_fim}")

    if caminho:
        total = sum(r[2] for r in resumo)
        print(f"\nArquivo final: {caminho}")
        print(f"Total de registros no BPA-I: {total}")
    else:
        print("\nNenhum registro gerado — nenhum paciente válido encontrado.")

    # CPF mal digitado/invalido ou nao cadastrado no Firebird: fica de fora da
    # producao por decisao do usuario (2026-07-15) -- so contagem, sem parar
    # a execucao nem listar em detalhe (evita ruido pra revisao mensal).
    if cpfs_invalidos:
        print(f"\nAVISO: {len(cpfs_invalidos)} CPF(s) invalido(s)/malformado(s) na planilha, excluido(s) da producao.")

    if nao_encontrados:
        print(f"\nAVISO: {len(nao_encontrados)} CPF(s) valido(s) mas nao cadastrado(s) na CADCNS, excluido(s) da producao.")

    if desconhecidos:
        print(f"\nAVISO: {len(desconhecidos)} celula(s) da coluna A nao reconhecida(s) (nem data, nem nutricionista, nem FDS/TODAS NUT):")
        for linha, val in desconhecidos:
            print(f"  linha Excel {linha}: {val!r}")


if __name__ == "__main__":
    main()
