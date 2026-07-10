"""
Reconstrucao de emergencia: S_PRD da competencia 06/2026 foi apagado por
completo (zerado) em 10/07/2026. Este script reconstroi a producao inteira
a partir dos arquivos BRUTOS de digitacao (DD-MM-2026.txt) em
C:\\BPA\\bpa_lotes -- a mesma fonte e a mesma logica que "Gerar BPA-I" usa
normalmente, so que gravando direto em S_PRD (bpa_gerador.calcular_atendimentos_producao)
em vez de escrever arquivo.

Regra de duplicidade (confirmada com o usuario): CPF repetido em SEQUENCIA
dentro do bloco do profissional = digitacao duplicada por engano, descarta
(ja e o que bpa_gerador.ler_arquivo_lote faz). CPF repetido em posicoes
DIFERENTES do mesmo bloco/dia = paciente atendido de novo de verdade,
mantem os dois -- NAO deduplicar isso.

Processa os arquivos em ordem cronologica; dentro de cada arquivo, os
grupos na ordem em que aparecem (ja consolidados por profissional+data
pelo proprio ler_arquivo_lote). calcular_atendimentos_producao recalcula
folha/sequencia a cada chamada consultando o S_PRD real (contar_producao_real),
entao nao ha risco de colisao mesmo processando muitos dias em sequencia --
so nao pode chamar duas vezes para o mesmo (profissional, dia).

Uso:
    python reconstruir_producao_202606.py             # dry-run, so mostra o plano
    python reconstruir_producao_202606.py --aplicar    # grava de verdade
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + r"\..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + r"\..")
import bpa_gerador as bpa

ARQUIVOS = [
    "02-06-2026.txt", "03-06-2026.txt", "08-06-2026.txt", "10-06-2026.txt",
    "14-06-2026.txt", "15-06-2026.txt", "16-06-2026.txt", "17-06-2026.txt",
    "19-06-2026.txt", "21-06-2026.txt",
]


def main(aplicar: bool):
    con = bpa.conectar()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM S_PRD")
    total_atual = cur.fetchone()[0]
    print(f"S_PRD tem {total_atual} linha(s) agora (esperado: 0, fresh start).\n")

    profs_raw = bpa.listar_profissionais(con)

    total_inseridos = 0
    total_nao_encontrados = []
    total_categoria_ambigua = []

    for nome_arquivo in ARQUIVOS:
        caminho = bpa.caminho_lote(nome_arquivo)
        grupos = bpa.ler_arquivo_lote(caminho)
        print(f"=== {nome_arquivo} — {len(grupos)} grupo(s) ===")

        for g in grupos:
            cns_raw = (g.get("cns") or "").strip()
            if not cns_raw:
                res = bpa.resolver_profissional_por_nome(profs_raw, g["medico_raw"])
                if res["status"] != "auto":
                    print(f"  ERRO: profissional '{g['medico_raw']}' nao resolvido automaticamente -- pulado.")
                    continue
                cns_raw = res["cns"]
            cns_prof = cns_raw.zfill(15)

            try:
                categoria, auto = bpa.detectar_categoria(con, cns_raw)
                if not auto or not categoria:
                    total_categoria_ambigua.append((nome_arquivo, g["medico_raw"]))
                    categoria = "medico"
            except Exception:
                categoria = "medico"

            try:
                dt = datetime.strptime(g["data"], "%d/%m/%Y")
                data_aten = dt.strftime("%Y%m%d")
            except (ValueError, KeyError):
                print(f"  ERRO: data invalida no grupo de {g['medico_raw']} -- pulado.")
                continue

            pacientes, nao_enc, invalidos = bpa.buscar_pacientes(con, g["documentos"])
            total_nao_encontrados.extend(nao_enc)

            if not pacientes:
                print(f"  {g['medico_raw']} ({categoria}) — nenhum paciente encontrado, pulado.")
                continue

            if aplicar:
                registros = bpa.calcular_atendimentos_producao(
                    con, cns_prof, categoria, data_aten, pacientes, gravar=True
                )
                folha_ini, seq_ini = registros[0]["folha"], registros[0]["seq"]
                folha_fim, seq_fim = registros[-1]["folha"], registros[-1]["seq"]
            else:
                folha_ini = seq_ini = folha_fim = seq_fim = "?"

            total_inseridos += len(pacientes)
            print(f"  {g['medico_raw']} ({categoria}, CNS {cns_prof}) — "
                  f"{len(pacientes)} atendimento(s) — folha/seq {folha_ini}/{seq_ini} a {folha_fim}/{seq_fim}"
                  + (f" — {len(nao_enc)} nao encontrado(s)" if nao_enc else ""))

        if aplicar:
            con.commit()

    print(f"\n=== RESUMO ===")
    print(f"Total de atendimentos {'gravados' if aplicar else 'planejados'}: {total_inseridos}")
    if total_nao_encontrados:
        print(f"Documentos nao encontrados na CADCNS ({len(total_nao_encontrados)}): {total_nao_encontrados}")
    if total_categoria_ambigua:
        print(f"Categoria ambigua, assumido 'medico' por padrao: {total_categoria_ambigua}")

    if not aplicar:
        print("\n(dry-run -- nada foi gravado. rode com --aplicar para gravar de verdade)")
    con.close()


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
