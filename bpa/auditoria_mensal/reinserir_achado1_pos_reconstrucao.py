"""
Depois da reconstrucao de emergencia de S_PRD (reconstruir_producao_202606.py,
10/07/2026), os 6 atendimentos do Achado 1 (lancados originalmente via
/api/pacientes/completar ou /api/conferencia/reenviar, nunca digitados no
arquivo bruto do dia) ficaram de fora -- a reconstrucao so le os arquivos
DD-MM-2026.txt (digitacao), e esses 6 nunca passaram por la.

Esses 6 JA ESTAO nos arquivos exportados (BPA_MEDICOS_*/BPA_ENFERMEIROS_*)
desde o patch aplicado hoje mais cedo (patch_lotes.py --aplicar). Este script
acha, comparando arquivo x banco (direcao inversa de patch_lotes.py: aqui o
arquivo tem mais que o banco, nao o contrario), os que faltam no banco agora
e insere via calcular_atendimentos_producao -- que calcula a folha/sequencia
CORRETA pos-reconstrucao (nao reaproveita a folha/sequencia antiga gravada
no arquivo, que colidiria com a nova numeracao).

Uso:
    python reinserir_achado1_pos_reconstrucao.py            # dry-run
    python reinserir_achado1_pos_reconstrucao.py --aplicar  # grava
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + r"\..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + r"\..")
import bpa_gerador as bpa

ALVOS = [("20260608", "08062026"), ("20260616", "16062026"), ("20260621", "21062026")]
ROTULO = {"medico": "MEDICOS", "enfermeiro": "ENFERMEIROS"}


def _ler_arquivo(caminho):
    with open(caminho, encoding="latin-1") as f:
        linhas = [l for l in f.read().splitlines() if l]
    return linhas[0], linhas[1:]


def main(aplicar: bool):
    con = bpa.conectar()
    cur = con.cursor()

    faltando = []  # (categoria, dtaten, cnspac, arquivo)
    for dtaten, ddmmaaaa in ALVOS:
        for categoria, cbo in [("medico", "225125"), ("enfermeiro", "223505")]:
            nome_arquivo = f"BPA_{ROTULO[categoria]}_{ddmmaaaa}.txt"
            caminho = os.path.join(bpa.BPA_LOTES_DIR, nome_arquivo)
            if not os.path.exists(caminho):
                continue
            _, detalhe = _ler_arquivo(caminho)
            existentes_arquivo = {
                (l[15:30].strip(), l[49:59].strip(), l[59:74].strip()) for l in detalhe
            }
            cur.execute(
                "SELECT PRD_CNSMED, PRD_PA, PRD_CNSPAC FROM S_PRD WHERE PRD_DTATEN = ? AND PRD_CBO = ?",
                (dtaten, cbo),
            )
            existentes_banco = {
                ((c or "").strip(), (p or "").strip(), (cp or "").strip())
                for c, p, cp in cur.fetchall()
            }
            for chave in existentes_arquivo - existentes_banco:
                cnsmed, pa, cnspac = chave
                faltando.append({
                    "categoria": categoria, "dtaten": dtaten, "cnsmed": cnsmed,
                    "cnspac": cnspac, "arquivo": nome_arquivo,
                })

    print(f"Faltando no banco (presentes no arquivo): {len(faltando)}")
    for f in faltando:
        print(f"  {f['arquivo']} — cnsmed={f['cnsmed']} cnspac={f['cnspac']} categoria={f['categoria']}")

    if not faltando:
        print("Nada a fazer.")
        con.close()
        return

    if not aplicar:
        print("\n(dry-run — nada foi gravado. rode com --aplicar para gravar)")
        con.close()
        return

    for f in faltando:
        pacientes, nao_encontrados, invalidos = bpa.buscar_pacientes(con, [f["cnspac"]])
        if not pacientes:
            print(f"  ERRO: paciente {f['cnspac']} nao encontrado na CADCNS — pulado ({nao_encontrados}, {invalidos})")
            continue
        registros = bpa.calcular_atendimentos_producao(
            con, f["cnsmed"], f["categoria"], f["dtaten"], pacientes, gravar=True
        )
        print(f"  Inserido: {f['arquivo']} cnspac={f['cnspac']} -> folha/seq {registros[0]['folha']}/{registros[0]['seq']}")

    con.commit()
    print("\nGravado.")
    con.close()


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
