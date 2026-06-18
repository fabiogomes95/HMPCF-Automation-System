"""
CLI fino para gerar o arquivo BPA-I a partir de um lote, sem precisar do
dashboard Streamlit rodando — útil pra testes manuais rápidos.

A lógica de verdade (layout, checksum, busca de pacientes, etc.) mora em
dashboard/bpa_gerador.py — fonte única, usada também pela página
dashboard/pages/4_BPA.py (Triagem/Digitação/Geração). Este script só
cuida da parte interativa de terminal (perguntar profissional/categoria
quando ambíguo), que no dashboard é resolvida por uma tela de confirmação.

Esse processo é separado de propósito do backend/frontend da Recepção —
só quem roda este script (ou abre o dashboard) tem acesso ao BPA.

Uso:
    python gerar_bpa_i.py --lote "C:/caminho/28-05-2026.txt"
"""

import argparse
import os
import sys
from datetime import datetime

_DASHBOARD_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "dashboard"))
sys.path.insert(0, _DASHBOARD_DIR)

import bpa_gerador as bpa  # noqa: E402


def _perguntar_categoria_manual():
    print("     1 - Médico")
    print("     2 - Enfermeiro")
    while True:
        op = input("   Escolha (1 ou 2): ").strip()
        if op in ("1", "2"):
            return "medico" if op == "1" else "enfermeiro"
        print("   Opção inválida.")


def _escolher_da_lista(profissionais):
    for i, (cns, nome) in enumerate(profissionais, 1):
        print(f"  {i:2d} - {nome:<40}  CNS: {cns}")
    while True:
        op = input("\nNúmero do profissional: ").strip()
        if op.isdigit() and 1 <= int(op) <= len(profissionais):
            return profissionais[int(op) - 1]
        print("   Opção inválida.")


def _resolver_categoria_interativo(con, cns_prof_raw):
    categoria, automatico = bpa.detectar_categoria(con, cns_prof_raw)
    print("   Categoria:")
    if automatico:
        print(f"     ✅ Detectada automaticamente via CBO cadastrado: {categoria.capitalize()}")
        return categoria
    if categoria:
        print(f"     ⚠️  Múltiplos CBOs cadastrados ({', '.join(categoria)}). Escolha manualmente:")
    else:
        print("     ⚠️  Nenhum CBO conhecido cadastrado para este profissional. Escolha manualmente:")
    return _perguntar_categoria_manual()


def _resolver_profissional_interativo(profissionais, nome_raw):
    resolucao = bpa.resolver_profissional_por_nome(profissionais, nome_raw)
    if resolucao["status"] == "auto":
        print(f"✅ Profissional '{nome_raw}' identificado automaticamente: {resolucao['nome']} (CNS {resolucao['cns']})")
        return resolucao["cns"], resolucao["nome"]
    if resolucao["status"] == "ambiguo":
        print(f"⚠️  Mais de um profissional cadastrado bate com '{nome_raw}'. Escolha:")
    else:
        print(f"⚠️  Nenhum profissional cadastrado bate com '{nome_raw}'. Escolha manualmente:")
    return _escolher_da_lista(resolucao["candidatos"])


def processar_lote(con, caminho_arquivo):
    grupos        = bpa.ler_arquivo_lote(caminho_arquivo)
    profissionais = bpa.listar_profissionais(con)

    todas_linhas   = []
    n_folhas_total = 0
    competencias   = []

    for grupo in grupos:
        medico_raw = grupo["medico_raw"]
        data_raw   = grupo["data"]
        documentos = grupo["documentos"]

        print(f"\n{'─' * 55}")
        print(f"Bloco: {medico_raw} | {data_raw} | {len(documentos)} documento(s)")

        try:
            data_dt = datetime.strptime(data_raw, "%d/%m/%Y")
        except ValueError:
            print(f"⚠️  Data inválida ('{data_raw}'), pulando bloco.")
            continue
        data_aten   = data_dt.strftime("%Y%m%d")
        competencia = data_aten[:6]

        cns_prof_raw, nome_prof = _resolver_profissional_interativo(profissionais, medico_raw)
        cns_prof  = cns_prof_raw.zfill(15)
        categoria = _resolver_categoria_interativo(con, cns_prof_raw)

        pacientes, nao_encontrados, invalidos = bpa.buscar_pacientes(con, documentos)
        if invalidos:
            print(f"⚠️  {len(invalidos)} valor(es) inválido(s) ignorado(s): {invalidos}")
        if nao_encontrados:
            print(f"⚠️  {len(nao_encontrados)} CNS/CPF não encontrado(s): {nao_encontrados}")
        if not pacientes:
            print("⚠️  Nenhum paciente encontrado neste bloco, pulando.")
            continue

        competencias.append(competencia)
        proc = bpa.PROCEDIMENTOS[categoria]["codigo"]
        cbo  = bpa.PROCEDIMENTOS[categoria]["cbo"]
        linhas, n_folhas = bpa.montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia)
        todas_linhas.extend(linhas)
        n_folhas_total += n_folhas
        print(f"   ✅ {len(linhas)} linha(s) geradas para {nome_prof.upper()} ({categoria})")

    if not todas_linhas:
        print("\n❌ Nenhuma linha gerada a partir do lote.")
        sys.exit(1)

    competencia_predominante = max(set(competencias), key=competencias.count)
    if len(set(competencias)) > 1:
        print(f"\n⚠️  O lote tem datas de competências diferentes ({sorted(set(competencias))}); "
              f"usando {competencia_predominante} no cabeçalho.")

    return todas_linhas, n_folhas_total, competencia_predominante


def main():
    ap = argparse.ArgumentParser(description="Gerador BPA-I — CLI (lê backend/app/services/bpa_gerador.py)")
    ap.add_argument("--lote", required=True, metavar="ARQUIVO",
                     help="Arquivo de lote (PROFISSIONAL: nome | DATA: dd/mm/aaaa)")
    args = ap.parse_args()

    print("=" * 55)
    print("  GERADOR BPA-I — CNES 2409283 (CLI)")
    print("=" * 55)

    try:
        con = bpa.conectar()
    except Exception as e:
        print(f"❌ Falha na conexão com o Firebird: {e}")
        sys.exit(1)

    try:
        linhas, n_folhas, competencia = processar_lote(con, args.lote)
    except bpa.LoteError as e:
        print(f"❌ {e}")
        sys.exit(1)
    finally:
        con.close()

    cabecalho = bpa.montar_cabecalho(competencia, len(linhas), n_folhas, linhas)
    ok, tam   = bpa.validar(linhas)
    print(f"\n{'✅' if ok else '⚠️ '} Validação: {len(linhas)} linha(s) de detalhe, {tam} chars cada")

    caminho = bpa.gerar_arquivo(linhas, cabecalho, competencia)
    print(f"\n✅ Arquivo: {caminho}")
    print(f"   Registros   : {len(linhas)}")
    print(f"   Folhas      : {n_folhas}")
    print(f"   Competência : {competencia[4:6]}/{competencia[:4]}")


if __name__ == "__main__":
    main()
