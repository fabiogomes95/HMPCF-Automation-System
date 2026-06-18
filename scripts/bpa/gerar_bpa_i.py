"""
Gerador de arquivo BPA-I — CNES 2409283
Layout DATASUS, encoding latin-1, CRLF

Uso:
    python gerar_bpa_i.py --entrada lista.txt          # banco Firebird real
    python gerar_bpa_i.py --mock --entrada lista.txt   # teste sem Firebird
    python gerar_bpa_i.py --mock                       # entrada interativa (mock)

Arquivo de entrada: uma linha por CNS (Cartão Nacional de Saúde, 15 dígitos).
Linhas começando com # são ignoradas.

O arquivo gerado fica em ~/Downloads/BPAI_2409283_AAAAMM.txt,
pronto para importar no BPA Magnético via:
    Menu > Importação > Importar Produção BPA

PENDÊNCIAS para verificar com o banco real (ver TODO no código):
  - Formato exato de DTNASC em CADCNS (string ou objeto date?)
  - Ordem dos campos de endereço (end/compl/num) — comparar com TXT exportado
  - CADMED possui coluna CBO? (atualmente não usada, categoria é escolhida manualmente)
  - CPF: se a lista de entrada tiver CPF, verificar qual coluna da CADCNS usar
"""

import sys
import os
import argparse
from datetime import date, datetime

# ── Configurações fixas da unidade ──────────────────────────────────────────
CNES           = "2409283"
MUNICIPIO      = "240360"
LOGRADOURO_COD = "081"
CEP_PADRAO     = "59575000"
RACA_PADRAO    = "03"    # parda
CARATER        = "02"    # urgência
CID            = "    "  # 4 espaços — não preenchido
ORGAO_RESP     = "SECRETARIA MUNICIPAL DE SAUDE"
ORGAO_DEST     = "SECRETARIA MUNICIPAL DE SAUDE"
VERSAO_SIST    = "3.10.00"

PROCEDIMENTOS = {
    "medico":     {"codigo": "0301060029", "cbo": "225125"},
    "enfermeiro": {"codigo": "0301010048", "cbo": "223505"},
}

DB_PATH = r"C:\BPA\BPAMAG.GDB"
DB_USER = "SYSDBA"
DB_PASS = "masterkey"


# ── Entrada de dados ─────────────────────────────────────────────────────────
def ler_lista_entrada(caminho_arquivo=None):
    """Retorna lista de CNS limpos. Aceita arquivo .txt ou digitação interativa."""
    if caminho_arquivo:
        if not os.path.exists(caminho_arquivo):
            print(f"❌ Arquivo não encontrado: {caminho_arquivo}")
            sys.exit(1)
        with open(caminho_arquivo, encoding="utf-8") as f:
            valores = [
                linha.strip().replace(".", "").replace("-", "").replace(" ", "")
                for linha in f
                if linha.strip() and not linha.strip().startswith("#")
            ]
        print(f"   {len(valores)} CNS carregados de '{caminho_arquivo}'.")
    else:
        print("\nDigite os CNS (um por linha). Linha em branco para finalizar:")
        valores = []
        while True:
            v = input("  > ").strip().replace(".", "").replace("-", "").replace(" ", "")
            if not v:
                break
            valores.append(v)
        print(f"   {len(valores)} CNS informados.")

    if not valores:
        print("❌ Nenhum CNS informado.")
        sys.exit(1)
    return valores


def pedir_data():
    while True:
        d = input("\nData de atendimento (DD/MM/AAAA): ").strip()
        try:
            dt = datetime.strptime(d, "%d/%m/%Y").date()
            return dt.strftime("%Y%m%d"), dt
        except ValueError:
            print("   Data inválida. Use DD/MM/AAAA.")


def pedir_competencia(data_str, _data_dt):
    comp = data_str[:6]  # AAAAMM
    print(f"Competência sugerida: {data_str[4:6]}/{data_str[:4]}")
    if input("Usar essa competência? (S/N): ").strip().upper() == "S":
        return comp
    while True:
        c = input("Competência (MM/AAAA): ").strip()
        try:
            datetime.strptime(c, "%m/%Y")
            return c[3:] + c[:2]  # → AAAAMM
        except ValueError:
            print("   Formato inválido. Use MM/AAAA.")


# ── Conexão Firebird ─────────────────────────────────────────────────────────
def conectar():
    try:
        import firebirdsql
    except ImportError:
        print("❌ Biblioteca não encontrada. Instale: pip install firebirdsql")
        sys.exit(1)
    try:
        con = firebirdsql.connect(
            host="localhost", database=DB_PATH,
            user=DB_USER, password=DB_PASS, charset="WIN1252",
        )
        print("✅ Conectado ao Firebird!\n")
        return con
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        sys.exit(1)


def escolher_profissional(con):
    cur = con.cursor()
    # TODO: se CADMED tiver coluna CBO, adicionar aqui para detectar categoria automaticamente
    cur.execute("SELECT CADMED_CNS, CADMED_NOME FROM CADMED ORDER BY CADMED_NOME")
    rows = cur.fetchall()
    if not rows:
        print("❌ Nenhum profissional encontrado no banco.")
        sys.exit(1)

    print("\nProfissionais cadastrados:")
    for i, (cns, nome) in enumerate(rows, 1):
        print(f"  {i:2d} - {str(nome).strip():<40}  CNS: {str(cns).strip()}")

    while True:
        op = input("\nNúmero do profissional: ").strip()
        if op.isdigit() and 1 <= int(op) <= len(rows):
            idx = int(op) - 1
            break
        print("   Opção inválida.")

    cns_prof  = str(rows[idx][0]).strip().zfill(15)
    nome_prof = str(rows[idx][1]).strip().upper()
    print(f"\n✅ Profissional: {nome_prof}")

    print("   Categoria:")
    print("     1 - Médico")
    print("     2 - Enfermeiro")
    while True:
        op2 = input("   Escolha (1 ou 2): ").strip()
        if op2 in ("1", "2"):
            categoria = "medico" if op2 == "1" else "enfermeiro"
            break
        print("   Opção inválida.")

    return categoria, cns_prof, nome_prof


# ── Busca de pacientes ───────────────────────────────────────────────────────
def _normalizar_dtnasc(valor):
    """
    Normaliza DTNASC para string AAAAMMDD.
    TODO: confirmar amanhã com o banco se vem como string ou objeto date.
    O código trata os dois casos.
    """
    if valor is None:
        return "19000101"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%Y%m%d")
    s = str(valor).strip().replace("/", "").replace("-", "")
    return s[:8] if len(s) >= 8 else "19000101"


def buscar_pacientes(con, lista_cns):
    """
    Busca somente os pacientes cujo CNS está na lista de entrada.
    TODO: se a lista de entrada tiver CPF, ajustar o WHERE para incluir
          a coluna de CPF da CADCNS (verificar nome da coluna no banco real).
    """
    cur = con.cursor()
    placeholders = ",".join("?" * len(lista_cns))
    cur.execute(f"""
        SELECT TRIM(CNS), DTNASC, TRIM(SEXO), IBGE, RACA, ETNIA, NACIONALIDADE,
               CO_LOGRAD, CEPPCN, LOGPCN, NUMPCN, CPLPCN, BAIRRO_PCNTE,
               DDTEL_PCNTE, TEL_PCNTE, EMAIL_PCNTE
        FROM CADCNS
        WHERE TRIM(CNS) IN ({placeholders})
          AND TRIM(CNS) <> ''
    """, lista_cns)

    encontrados = set()
    pacientes   = []

    for row in cur.fetchall():
        cns    = str(row[0]).strip().zfill(15)
        nasc   = _normalizar_dtnasc(row[1])
        sexo   = str(row[2]).strip()[0].upper() if row[2] else "M"
        ibge   = str(row[3]).strip().zfill(6)    if row[3]  else MUNICIPIO
        raca   = str(row[4]).strip().zfill(2)    if row[4]  else RACA_PADRAO
        etnia  = str(row[5]).strip().zfill(4)    if row[5]  else "0000"
        nac    = str(row[6]).strip().zfill(3)    if row[6]  else "010"
        lograd = str(row[7]).strip().zfill(3)    if row[7]  else LOGRADOURO_COD
        cep    = str(row[8]).strip().replace("-", "").zfill(8) if row[8] else CEP_PADRAO
        end_   = str(row[9]).strip()[:30].ljust(30)  if row[9]  else " " * 30
        # TODO: verificar amanhã com arquivo TXT real a ordem correta de compl/num
        compl  = str(row[10]).strip()[:10].ljust(10) if row[10] else " " * 10
        num    = str(row[11]).strip()[:5].ljust(5)   if row[11] else " " * 5
        bairro = str(row[12]).strip()[:30].ljust(30) if row[12] else " " * 30
        ddd    = str(row[13]).strip()[:2].ljust(2)   if row[13] else "  "
        tel    = str(row[14]).strip()[:9].ljust(9)   if row[14] else " " * 9
        email  = str(row[15]).strip()[:40].ljust(40) if row[15] else " " * 40

        pacientes.append({
            "cns": cns, "nasc": nasc, "sexo": sexo,
            "ibge": ibge, "raca": raca, "etnia": etnia, "nac": nac,
            "lograd": lograd, "cep": cep, "end": end_,
            "compl": compl, "num": num, "bairro": bairro,
            "ddd": ddd, "tel": tel, "email": email,
        })
        encontrados.add(str(row[0]).strip())

    nao_encontrados = set(lista_cns) - encontrados
    if nao_encontrados:
        print(f"\n⚠️  {len(nao_encontrados)} CNS não encontrado(s) na CADCNS:")
        for v in sorted(nao_encontrados):
            print(f"   - {v}")

    return pacientes


# ── Modo mock ────────────────────────────────────────────────────────────────
_MOCK_NASCIMENTOS = [
    ("19850315", "M"), ("19921022", "F"), ("19780603", "M"),
    ("20001201", "F"), ("19650814", "M"), ("19900507", "F"),
]


def mock_profissional():
    print("\n[MOCK] Profissional: DR TESTE MOCK — Médico\n")
    return "medico", "700000000000001", "DR TESTE MOCK"


def mock_pacientes(lista_cns):
    print(f"[MOCK] Gerando {len(lista_cns)} paciente(s) fictício(s).\n")
    pacientes = []
    for i, cns_raw in enumerate(lista_cns):
        nasc, sexo = _MOCK_NASCIMENTOS[i % len(_MOCK_NASCIMENTOS)]
        pacientes.append({
            "cns":    cns_raw.zfill(15),
            "nasc":   nasc,
            "sexo":   sexo,
            "ibge":   MUNICIPIO,
            "raca":   RACA_PADRAO,
            "etnia":  "0000",
            "nac":    "010",
            "lograd": LOGRADOURO_COD,
            "cep":    CEP_PADRAO,
            "end":    "RUA DE TESTE MOCK".ljust(30),
            "compl":  "APTO 1    ",
            "num":    "100  ",
            "bairro": "CENTRO".ljust(30),
            "ddd":    "84",
            "tel":    "999999999",
            "email":  " " * 40,
        })
    return pacientes


# ── Montagem do layout BPA-I ─────────────────────────────────────────────────
def _calcular_idade(nasc_str, ref):
    try:
        d = date(int(nasc_str[:4]), int(nasc_str[4:6]), int(nasc_str[6:8]))
        return ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))
    except Exception:
        return 0


def _linha_detalhe(pac, proc, cbo, cns_prof, data_aten, competencia, folha, seq):
    ref   = date(int(data_aten[:4]), int(data_aten[4:6]), int(data_aten[6:8]))
    idade = _calcular_idade(pac["nasc"], ref)
    return (
        "03"                                       # 02 | tipo registro
        + CNES.zfill(7)                            # 07 | CNES
        + competencia                              # 06 | competência AAAAMM
        + cns_prof.zfill(15)                       # 15 | CNS profissional
        + cbo.ljust(6)                             # 06 | CBO
        + data_aten                                # 08 | data atendimento AAAAMMDD
        + str(folha).zfill(3)                      # 03 | número da folha
        + str(seq).zfill(2)                        # 02 | sequência na folha (01-99)
        + proc.zfill(10)                           # 10 | procedimento
        + pac["cns"].zfill(15)                     # 15 | CNS paciente
        + pac["sexo"][0].ljust(2)                  # 02 | sexo
        + pac["ibge"].zfill(6)                     # 06 | município IBGE
        + CID                                      # 04 | CID (espaços)
        + " "                                      # 01 | reservado
        + str(idade).zfill(3)                      # 03 | idade calculada
        + "000001"                                 # 06 | quantidade
        + CARATER                                  # 02 | caráter atendimento
        + " " * 13                                 # 13 | autorização
        + "BPA"                                    # 03 | origem
        + pac["nasc"]                              # 08 | data nascimento AAAAMMDD
        + "I"                                      # 01 | tipo BPA (Individualizado)
        + pac["raca"].zfill(2)                     # 02 | raça/cor
        + pac["etnia"].zfill(4)                    # 04 | etnia
        + pac["nac"].zfill(3)                      # 03 | nacionalidade
        + "   "                                    # 03 | serviço
        + "   "                                    # 03 | classificação
        + "0000"                                   # 04 | equipe sequência
        + "000000"                                 # 06 | equipe área
        + pac["lograd"].zfill(3)                   # 03 | código logradouro
        + pac["cep"].zfill(8)                      # 08 | CEP
        + pac["end"]                               # 30 | logradouro/endereço
        + pac["compl"]                             # 10 | complemento  ← TODO: verificar ordem
        + pac["num"]                               # 05 | número       ← TODO: verificar ordem
        + pac["bairro"]                            # 30 | bairro
        + pac["ddd"]                               # 02 | DDD
        + pac["tel"]                               # 09 | telefone
        + pac["email"]                             # 40 | e-mail
    )                                              # Total esperado: 285 chars


def montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia):
    linhas = []
    folha  = 1
    seq    = 1
    for pac in pacientes:
        if seq > 99:
            seq = 1
            folha += 1
        linhas.append(
            _linha_detalhe(pac, proc, cbo, cns_prof, data_aten, competencia, folha, seq)
        )
        seq += 1
    return linhas, folha


def montar_cabecalho(competencia, n_linhas, n_folhas):
    return (
        "01"
        + "#BPA#"
        + competencia
        + str(n_linhas).zfill(6)
        + str(n_folhas).zfill(6)
        + "0000"
        + VERSAO_SIST.ljust(10)
        + ORGAO_RESP[:30].ljust(30)
        + "00000000000000"
        + ORGAO_DEST[:40].ljust(40)
        + " " * 10
    )


# ── Validação ────────────────────────────────────────────────────────────────
def _validar(linhas):
    if not linhas:
        return True, 0
    tam    = len(linhas[0])
    erros  = [i + 1 for i, l in enumerate(linhas) if len(l) != tam]
    if erros:
        print(f"   ⚠️  Linhas com tamanho divergente: {erros}")
        return False, tam
    return True, tam


# ── Escrita do arquivo ───────────────────────────────────────────────────────
def gerar_arquivo(linhas, cabecalho, competencia):
    pasta = os.path.join(os.path.expanduser("~"), "Downloads")
    nome  = os.path.join(pasta, f"BPAI_{CNES}_{competencia}.txt")
    # newline="" garante CRLF real sem duplicação em qualquer plataforma
    with open(nome, "w", encoding="latin-1", newline="") as f:
        f.write(cabecalho + "\r\n")
        for linha in linhas:
            f.write(linha + "\r\n")
    return nome


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Gerador BPA-I — CNES 2409283")
    ap.add_argument("--mock",    action="store_true", help="Modo teste sem Firebird (dados fictícios)")
    ap.add_argument("--entrada", metavar="ARQUIVO",   help="Arquivo .txt com CNS, um por linha")
    args = ap.parse_args()

    print("=" * 55)
    print("  GERADOR BPA-I  —  CNES 2409283")
    if args.mock:
        print("  *** MODO MOCK — dados fictícios ***")
    print("=" * 55)

    data_str, data_dt = pedir_data()
    competencia       = pedir_competencia(data_str, data_dt)
    lista_cns         = ler_lista_entrada(args.entrada)

    if args.mock:
        categoria, cns_prof, nome_prof = mock_profissional()
        pacientes = mock_pacientes(lista_cns)
    else:
        con = conectar()
        categoria, cns_prof, nome_prof = escolher_profissional(con)
        print(f"\n📥 Buscando {len(lista_cns)} paciente(s) no banco...")
        pacientes = buscar_pacientes(con, lista_cns)
        con.close()

    if not pacientes:
        print("❌ Nenhum paciente encontrado. Arquivo não gerado.")
        sys.exit(1)

    proc = PROCEDIMENTOS[categoria]["codigo"]
    cbo  = PROCEDIMENTOS[categoria]["cbo"]

    linhas, n_folhas = montar_linhas(pacientes, proc, cbo, cns_prof, data_str, competencia)
    cabecalho        = montar_cabecalho(competencia, len(linhas), n_folhas)

    ok, tam  = _validar(linhas)
    icone    = "✅" if ok else "⚠️ "
    print(f"\n{icone} Validação: {len(linhas)} linha(s) de detalhe, {tam} chars cada")

    caminho = gerar_arquivo(linhas, cabecalho, competencia)

    print(f"✅ Arquivo: {caminho}")
    print(f"   Profissional: {nome_prof} ({categoria})")
    print(f"   Registros   : {len(linhas)}")
    print(f"   Folhas      : {n_folhas}")
    print(f"   Competência : {competencia[4:6]}/{competencia[:4]}")
    if args.mock:
        print(f"\n   Para testar com banco real:")
        print(f"   python gerar_bpa_i.py --entrada lista_exemplo.txt")


if __name__ == "__main__":
    main()
