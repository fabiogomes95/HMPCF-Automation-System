"""
Gerador de arquivo BPA-I — CNES 2409283
Layout DATASUS, encoding latin-1, CRLF

Uso:
    python gerar_bpa_i.py --entrada lista.txt          # banco Firebird real
    python gerar_bpa_i.py --mock --entrada lista.txt   # teste sem Firebird
    python gerar_bpa_i.py --mock                       # entrada interativa (mock)
    python gerar_bpa_i.py --lote "C:/caminho/28-05-2026.txt"  # lote legado, banco real

Arquivo de entrada (--entrada): uma linha por CNS (15 dígitos) ou CPF
(11 dígitos). Linhas começando com # são ignoradas.

Arquivo de lote (--lote): formato usado pelo robô antigo
(legado/automacao/<DD-MM-AAAA>.txt), com blocos:
    PROFISSIONAL: <nome> | DATA: DD/MM/AAAA
    <CNS ou CPF>
    <CNS ou CPF>
    PROFISSIONAL: <outro nome> | DATA: DD/MM/AAAA
    ...
O profissional é identificado automaticamente pelo nome (CADMED); se não
achar (ou achar mais de um), pergunta ao usuário. Documentos repetidos no
mesmo bloco geram uma linha cada (o mesmo paciente pode ter mais de um
atendimento no dia — não são deduplicados).

O arquivo gerado fica em ~/Downloads/BPAI_2409283_AAAAMM.txt,
pronto para importar no BPA Magnético via:
    Menu > Importação > Importar Produção BPA

Confirmado em 2026-06-18 contra o banco Firebird real (somente leitura) e
contra um arquivo .MAR já exportado pelo BPA Magnético em produção
(C:/BPA/EXPORTA/PAkauan-.MAR) comparado byte a byte com o layout oficial
DATASUS (C:/BPA/Layout_Exportacao_BPA.pdf):
  - O layout BPA-I real tem 350 caracteres de dados por linha (não 285).
    O layout antigo deste script estava desatualizado e foi reescrito.
  - DTNASC em CADCNS vem como string AAAAMMDD (não objeto date)
  - Ordem real dos campos de endereço: end/compl/num/bairro — já correta
  - Categoria (médico/enfermeiro) é detectada automaticamente via CADMED_CBO_CNES
  - CPF é aceito via coluna NUM_CPF da CADCNS, junto com CNS
  - prd-org = "BPA" está CORRETO (o "BPI" visto em S_PRD.PRD_ORG é um código
    interno do banco, não o campo "origem" do arquivo exportado)
  - Checksum do cabeçalho (cbc-smt-vrf) verificado e reproduzido com sucesso
    contra o arquivo .MAR real: soma(procedimento + quantidade) de todas as
    linhas, resto da divisão por 1111, + 1111
"""

import sys
import os
import argparse
from datetime import date, datetime

# ── Configurações fixas da unidade ──────────────────────────────────────────
# ORGAO_RESP, SIGLA_ORGAO, CNPJ_PRESTADOR, ORGAO_DEST e DESTINO_INDICADOR
# copiados literalmente do cabeçalho de C:\BPA\EXPORTA\PAkauan-.MAR (export
# real já aceito em produção), para garantir compatibilidade exata.
CNES               = "2409283"
MUNICIPIO          = "240360"
LOGRADOURO_COD     = "081"
CEP_PADRAO         = "59575000"
RACA_PADRAO        = "03"    # parda
CARATER            = "02"    # urgência
CID                = "    "  # 4 espaços — não preenchido
ORGAO_RESP         = "sms extremoz"
SIGLA_ORGAO        = "sms"
CNPJ_PRESTADOR     = "08204497000171"
ORGAO_DEST         = "secretaria municipal de saude"
DESTINO_INDICADOR  = "M"     # M = Municipal, E = Estadual
VERSAO_SIST        = "3.10.00"

PROCEDIMENTOS = {
    "medico":     {"codigo": "0301060029", "cbo": "225125"},
    "enfermeiro": {"codigo": "0301010048", "cbo": "223505"},
}
CBO_PARA_CATEGORIA = {info["cbo"]: categoria for categoria, info in PROCEDIMENTOS.items()}

DB_PATH = r"C:\BPA\BPAMAG.GDB"
DB_USER = "SYSDBA"
DB_PASS = "masterkey"


# ── Entrada de dados ─────────────────────────────────────────────────────────
def ler_lista_entrada(caminho_arquivo=None):
    """Retorna lista de CNS/CPF limpos (apenas dígitos). Aceita arquivo .txt ou digitação interativa."""
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


def ler_arquivo_lote(caminho_arquivo):
    """
    Lê um arquivo no formato legado (usado pelo robô antigo em
    legado/automacao/<DD-MM-AAAA>.txt):

        PROFISSIONAL: <nome> | DATA: DD/MM/AAAA
        <CNS ou CPF>
        <CNS ou CPF>
        PROFISSIONAL: <outro nome> | DATA: DD/MM/AAAA
        ...

    O mesmo profissional pode aparecer em mais de um bloco no mesmo dia —
    os documentos são agrupados por (nome, data), preservando a ordem e as
    repetições (o mesmo paciente pode ter mais de um atendimento no dia).

    Retorna lista de dicts: [{"medico_raw": str, "data": "DD/MM/AAAA", "documentos": [...]}]
    """
    if not os.path.exists(caminho_arquivo):
        print(f"❌ Arquivo não encontrado: {caminho_arquivo}")
        sys.exit(1)

    with open(caminho_arquivo, encoding="utf-8") as f:
        linhas_arquivo = f.readlines()

    grupos = {}  # (medico_raw, data) -> dict
    ordem  = []
    grupo_atual = None

    for linha in linhas_arquivo:
        linha = linha.strip()
        if not linha:
            continue

        if "PROFISSIONAL:" in linha.upper():
            partes     = linha.split("|")
            medico_raw = partes[0].split(":", 1)[1].strip() if ":" in partes[0] else partes[0].strip()
            data_raw   = partes[1].split(":", 1)[1].strip() if len(partes) > 1 and ":" in partes[1] else ""
            chave = (medico_raw.upper(), data_raw)
            if chave not in grupos:
                grupos[chave] = {"medico_raw": medico_raw, "data": data_raw, "documentos": []}
                ordem.append(chave)
            grupo_atual = grupos[chave]
        elif grupo_atual is not None:
            doc = linha.replace(".", "").replace("-", "").replace(" ", "")
            if doc:
                grupo_atual["documentos"].append(doc)

    if not ordem:
        print(f"❌ Nenhum bloco 'PROFISSIONAL: ... | DATA: ...' encontrado em '{caminho_arquivo}'.")
        sys.exit(1)

    return [grupos[chave] for chave in ordem]


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


def _perguntar_categoria_manual():
    print("     1 - Médico")
    print("     2 - Enfermeiro")
    while True:
        op2 = input("   Escolha (1 ou 2): ").strip()
        if op2 in ("1", "2"):
            return "medico" if op2 == "1" else "enfermeiro"
        print("   Opção inválida.")


def listar_profissionais(con):
    """Retorna [(cns_raw, nome), ...] de todos os profissionais cadastrados."""
    cur = con.cursor()
    cur.execute("SELECT CADMED_CNS, CADMED_NOME FROM CADMED ORDER BY CADMED_NOME")
    rows = cur.fetchall()
    return [(str(cns).strip(), str(nome).strip()) for cns, nome in rows]


def detectar_categoria(con, cns_prof_raw):
    """
    Detecta médico/enfermeiro via CADMED_CBO_CNES.
    Retorna (categoria, automatico). Se automatico=False, categoria é None
    (sem CBO conhecido) ou uma lista de categorias possíveis (múltiplos CBOs).
    """
    cur = con.cursor()
    cur.execute("SELECT MED_CBO FROM CADMED_CBO_CNES WHERE MED_CNS = ?", (cns_prof_raw,))
    cbos_cadastrados   = {str(r[0]).strip() for r in cur.fetchall()}
    categorias_validas = sorted({CBO_PARA_CATEGORIA[c] for c in cbos_cadastrados if c in CBO_PARA_CATEGORIA})

    if len(categorias_validas) == 1:
        return categorias_validas[0], True
    return categorias_validas, False


def resolver_categoria_interativo(con, cns_prof_raw):
    """Detecta a categoria automaticamente; pede ao usuário se for ambíguo/desconhecido."""
    categoria, automatico = detectar_categoria(con, cns_prof_raw)
    print("   Categoria:")
    if automatico:
        print(f"     ✅ Detectada automaticamente via CBO cadastrado: {categoria.capitalize()}")
        return categoria
    if categoria:  # lista com mais de uma categoria possível
        print(f"     ⚠️  Múltiplos CBOs cadastrados ({', '.join(categoria)}). Escolha manualmente:")
    else:
        print("     ⚠️  Nenhum CBO conhecido cadastrado para este profissional. Escolha manualmente:")
    return _perguntar_categoria_manual()


def _escolher_da_lista(profissionais):
    """Mostra a lista numerada e pede ao usuário para escolher um índice."""
    for i, (cns, nome) in enumerate(profissionais, 1):
        print(f"  {i:2d} - {nome:<40}  CNS: {cns}")

    while True:
        op = input("\nNúmero do profissional: ").strip()
        if op.isdigit() and 1 <= int(op) <= len(profissionais):
            return profissionais[int(op) - 1]
        print("   Opção inválida.")


def escolher_profissional(con):
    profissionais = listar_profissionais(con)
    if not profissionais:
        print("❌ Nenhum profissional encontrado no banco.")
        sys.exit(1)

    print("\nProfissionais cadastrados:")
    cns_prof_raw, nome_prof = _escolher_da_lista(profissionais)
    cns_prof  = cns_prof_raw.zfill(15)
    nome_prof = nome_prof.upper()
    print(f"\n✅ Profissional: {nome_prof}")

    categoria = resolver_categoria_interativo(con, cns_prof_raw)
    return categoria, cns_prof, nome_prof


def resolver_profissional_por_nome(con, profissionais, nome_raw):
    """
    Tenta achar o profissional pelo nome (como vem do arquivo legado, ex.
    "RAFHAELA LOPES" ou só "STELA") comparando tokens contra CADMED_NOME.
    Todo token do nome_raw precisa aparecer como palavra inteira no nome
    cadastrado (evita falso-positivo tipo "STELA" casar com "ESTELA").

    Se achar exatamente 1: usa automaticamente.
    Se achar 0 ou mais de 1: pede para o usuário escolher manualmente
    (entre os candidatos achados, ou na lista completa se não achou nenhum).
    """
    tokens = nome_raw.upper().split()
    candidatos = [
        (cns, nome) for cns, nome in profissionais
        if all(tok in nome.upper().split() for tok in tokens)
    ]

    if len(candidatos) == 1:
        cns_raw, nome = candidatos[0]
        print(f"✅ Profissional '{nome_raw}' identificado automaticamente: {nome} (CNS {cns_raw})")
        return cns_raw, nome

    if candidatos:
        print(f"⚠️  Mais de um profissional cadastrado bate com '{nome_raw}'. Escolha:")
        return _escolher_da_lista(candidatos)

    print(f"⚠️  Nenhum profissional cadastrado bate com '{nome_raw}'. Escolha manualmente:")
    return _escolher_da_lista(profissionais)


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


def _buscar_dados_pacientes(con, cns_list, cpf_list):
    """Consulta a CADCNS e retorna {documento: dados} para CNS e CPF buscados."""
    cns_unicos = list(set(cns_list))
    cpf_unicos = list(set(cpf_list))

    condicoes = []
    params    = []
    if cns_unicos:
        condicoes.append(f"(CNS IN ({','.join('?' * len(cns_unicos))}) AND CNS <> '')")
        params.extend(cns_unicos)
    if cpf_unicos:
        condicoes.append(f"(NUM_CPF IN ({','.join('?' * len(cpf_unicos))}) AND NUM_CPF <> '')")
        params.extend(cpf_unicos)

    if not condicoes:
        return {}

    cur = con.cursor()
    cur.execute(f"""
        SELECT CNS, NOME, DTNASC, SEXO, IBGE, RACA, ETNIA, NACIONALIDADE,
               CO_LOGRAD, CEPPCN, LOGPCN, NUMPCN, CPLPCN, BAIRRO_PCNTE,
               DDTEL_PCNTE, TEL_PCNTE, EMAIL_PCNTE, NUM_CPF
        FROM CADCNS
        WHERE {' OR '.join(condicoes)}
    """, params)

    por_documento = {}
    for row in cur.fetchall():
        cns    = str(row[0]).strip().zfill(15)
        nome   = str(row[1]).strip()[:30].ljust(30).upper() if row[1] else " " * 30
        nasc   = _normalizar_dtnasc(row[2])
        sexo   = str(row[3]).strip()[0].upper() if row[3] else "M"
        ibge   = str(row[4]).strip().zfill(6)    if row[4]  else MUNICIPIO
        raca   = str(row[5]).strip().zfill(2)    if row[5]  else RACA_PADRAO
        # prd-etnia só é preenchido quando raça/cor = 05 (indígena); nos
        # demais casos o layout oficial exige o campo em branco (espaços).
        etnia  = str(row[6]).strip().zfill(4)    if row[6] and raca == "05" else "    "
        nac    = str(row[7]).strip().zfill(3)    if row[7]  else "010"
        lograd = str(row[8]).strip().zfill(3)    if row[8]  else LOGRADOURO_COD
        cep    = str(row[9]).strip().replace("-", "").zfill(8) if row[9] else CEP_PADRAO
        end_   = str(row[10]).strip()[:30].ljust(30) if row[10] else " " * 30
        num    = str(row[11]).strip()[:5].ljust(5)   if row[11] else " " * 5
        compl  = str(row[12]).strip()[:10].ljust(10) if row[12] else " " * 10
        bairro = str(row[13]).strip()[:30].ljust(30) if row[13] else " " * 30
        ddd    = str(row[14]).strip()[:2].ljust(2)   if row[14] else "  "
        tel    = str(row[15]).strip()[:9].ljust(9)   if row[15] else " " * 9
        email  = str(row[16]).strip()[:40].ljust(40) if row[16] else " " * 40
        cpf    = str(row[17]).strip() if row[17] else ""

        dados = {
            "cns": cns, "nome": nome, "nasc": nasc, "sexo": sexo,
            "ibge": ibge, "raca": raca, "etnia": etnia, "nac": nac,
            "lograd": lograd, "cep": cep, "end": end_,
            "compl": compl, "num": num, "bairro": bairro,
            "ddd": ddd, "tel": tel, "email": email, "cpf": cpf,
        }
        por_documento[str(row[0]).strip()] = dados
        if cpf:
            por_documento[cpf] = dados

    return por_documento


def buscar_pacientes(con, lista_valores):
    """
    Busca os pacientes cujo CNS (15 dígitos) ou CPF (11 dígitos, coluna
    NUM_CPF) está na lista de entrada.

    Retorna a lista na MESMA ORDEM e com as MESMAS REPETIÇÕES da entrada —
    cada ocorrência representa um atendimento distinto (ex.: o mesmo CNS
    pode aparecer duas vezes no dia, para dois procedimentos diferentes) —
    pulando os valores que não foram encontrados na CADCNS.
    """
    cns_list = [v for v in lista_valores if len(v) == 15]
    cpf_list = [v for v in lista_valores if len(v) == 11]
    invalidos = [v for v in lista_valores if v not in cns_list and v not in cpf_list]
    if invalidos:
        print(f"\n⚠️  {len(invalidos)} valor(es) com tamanho inválido (nem CNS-15 nem CPF-11), ignorado(s):")
        for v in invalidos:
            print(f"   - {v}")

    por_documento = _buscar_dados_pacientes(con, cns_list, cpf_list)

    pacientes       = []
    nao_encontrados = set()
    for v in lista_valores:
        if v in invalidos:
            continue
        dados = por_documento.get(v)
        if dados:
            pacientes.append(dados)
        else:
            nao_encontrados.add(v)

    if nao_encontrados:
        print(f"\n⚠️  {len(nao_encontrados)} CNS/CPF não encontrado(s) na CADCNS:")
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
            "nome":   f"PACIENTE MOCK {i + 1}".ljust(30),
            "nasc":   nasc,
            "sexo":   sexo,
            "ibge":   MUNICIPIO,
            "raca":   RACA_PADRAO,
            "etnia":  "    ",
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
            "cpf":    "",
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
    """
    Layout BPA-I oficial (350 chars), conforme C:/BPA/Layout_Exportacao_BPA.pdf
    e confirmado byte a byte contra C:/BPA/EXPORTA/PAkauan-.MAR (export real).
    """
    ref   = date(int(data_aten[:4]), int(data_aten[4:6]), int(data_aten[6:8]))
    idade = _calcular_idade(pac["nasc"], ref)
    cpf   = pac["cpf"].zfill(11) if pac["cpf"] else " " * 11
    return (
        "03"                                       # 002 | prd-ident
        + CNES.zfill(7)                             # 007 | prd-cnes
        + competencia                               # 006 | prd-cmp
        + cns_prof.zfill(15)                        # 015 | prd_cnsmed
        + cbo.ljust(6)                               # 006 | prd_cbo
        + data_aten                                 # 008 | prd_dtaten
        + str(folha).zfill(3)                       # 003 | prd-flh
        + str(seq).zfill(2)                         # 002 | prd-seq
        + proc.zfill(10)                            # 010 | prd-pa
        + pac["cns"].zfill(15)                      # 015 | prd-cnspac
        + pac["sexo"][0]                            # 001 | prd-sexo
        + pac["ibge"].zfill(6)                      # 006 | prd-ibge
        + CID                                       # 004 | prd-cid
        + str(idade).zfill(3)                       # 003 | prd-ldade
        + "000001"                                  # 006 | prd-qt
        + CARATER                                   # 002 | prd-caten
        + " " * 13                                  # 013 | prd-naut
        + "BPA"                                     # 003 | prd-org
        + pac["nome"]                                # 030 | prd-nmpac
        + pac["nasc"]                                # 008 | prd-dtnasc
        + pac["raca"].zfill(2)                       # 002 | prd-raca
        + pac["etnia"].zfill(4)                      # 004 | prd-etnia
        + pac["nac"].zfill(3)                        # 003 | prd-nac
        + "   "                                      # 003 | prd_srv
        + "   "                                      # 003 | prd_clf
        + " " * 8                                    # 008 | prd_equipe_seq
        + " " * 4                                    # 004 | prd_equipe_area
        + " " * 14                                   # 014 | prd_cnpj
        + pac["cep"].zfill(8)                        # 008 | prd_cep_pcnte
        + pac["lograd"].zfill(3)                     # 003 | prd_lograd_pcnte
        + pac["end"]                                  # 030 | prd_end_pcnte
        + pac["compl"]                                # 010 | prd_compl_pcnte
        + pac["num"]                                  # 005 | prd_num_pcnte
        + pac["bairro"]                               # 030 | prd_bairro_pcnte
        + pac["ddd"] + pac["tel"]                      # 011 | prd_ddtel_pcnte (DDD+telefone)
        + pac["email"]                                 # 040 | prd_email_pcnte
        + " " * 10                                   # 010 | prd_ine
        + cpf                                        # 011 | prd_cpf_pcnte
        + " "                                        # 001 | prd_situacao_rua
    )                                              # Total: 350 chars


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


def _calcular_checksum(linhas):
    """
    cbc-smt-vrf: soma do código do procedimento (prd-pa) + quantidade
    (prd-qt) de cada linha, resto da divisão por 1111, + 1111. Fórmula
    confirmada reproduzindo o checksum real de C:/BPA/EXPORTA/PAkauan-.MAR.
    Lê os valores diretamente das linhas já montadas (posições 49-59 e
    88-94), então funciona mesmo com procedimentos diferentes misturados
    (ex.: lote com médico e enfermeiro no mesmo arquivo).
    """
    total = sum(int(l[49:59]) + int(l[88:94]) for l in linhas)
    return str(total % 1111 + 1111).zfill(4)


def montar_cabecalho(competencia, n_linhas, n_folhas, linhas):
    checksum = _calcular_checksum(linhas)
    return (
        "01"                                  # 002 | cbc-hdr
        + "#BPA#"                             # 005 | cbc-hdr2
        + competencia                         # 006 | cbc-mvm
        + str(n_linhas).zfill(6)              # 006 | cbc-lin
        + str(n_folhas).zfill(6)              # 006 | cbc-flh
        + checksum                            # 004 | cbc-smt-vrf
        + ORGAO_RESP[:30].ljust(30)           # 030 | cbc-rsp
        + SIGLA_ORGAO[:6].ljust(6)            # 006 | cbc-sgl
        + CNPJ_PRESTADOR.zfill(14)            # 014 | cbc-cgccpf
        + ORGAO_DEST[:40].ljust(40)           # 040 | cbc-dst
        + DESTINO_INDICADOR                   # 001 | cbc-dst-in
        + VERSAO_SIST[:10].ljust(10)          # 010 | cbc_versao
    )                                         # Total: 130 chars


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


def processar_lote(con, caminho_arquivo):
    """
    Processa um arquivo no formato legado (vários profissionais/blocos para
    um ou mais dias) e devolve (linhas, n_folhas_total, competencia) prontos
    para gerar_arquivo(). Cada profissional tem sua própria contagem de
    folha/seq reiniciada (igual ao comportamento confirmado em produção).
    """
    grupos        = ler_arquivo_lote(caminho_arquivo)
    profissionais = listar_profissionais(con)

    todas_linhas  = []
    n_folhas_total = 0
    competencias   = []

    for grupo in grupos:
        medico_raw = grupo["medico_raw"]
        data_raw   = grupo["data"]
        documentos = grupo["documentos"]

        print(f"\n{'─' * 55}")
        print(f"Bloco: {medico_raw} | {data_raw} | {len(documentos)} documento(s)")

        try:
            data_dt  = datetime.strptime(data_raw, "%d/%m/%Y")
        except ValueError:
            print(f"⚠️  Data inválida ('{data_raw}'), pulando bloco.")
            continue
        data_aten   = data_dt.strftime("%Y%m%d")
        competencia = data_aten[:6]
        competencias.append(competencia)

        cns_prof_raw, nome_prof = resolver_profissional_por_nome(con, profissionais, medico_raw)
        cns_prof  = cns_prof_raw.zfill(15)
        categoria = resolver_categoria_interativo(con, cns_prof_raw)

        pacientes = buscar_pacientes(con, documentos)
        if not pacientes:
            print("⚠️  Nenhum paciente encontrado neste bloco, pulando.")
            continue

        proc = PROCEDIMENTOS[categoria]["codigo"]
        cbo  = PROCEDIMENTOS[categoria]["cbo"]
        linhas, n_folhas = montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia)
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


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Gerador BPA-I — CNES 2409283")
    ap.add_argument("--mock",    action="store_true", help="Modo teste sem Firebird (dados fictícios)")
    ap.add_argument("--entrada", metavar="ARQUIVO",   help="Arquivo .txt com CNS ou CPF, um por linha")
    ap.add_argument("--lote",    metavar="ARQUIVO",   help="Arquivo legado (PROFISSIONAL: ... | DATA: ...) com vários profissionais/dia")
    args = ap.parse_args()

    print("=" * 55)
    print("  GERADOR BPA-I  —  CNES 2409283")
    if args.mock:
        print("  *** MODO MOCK — dados fictícios ***")
    print("=" * 55)

    if args.lote:
        con = conectar()
        linhas, n_folhas, competencia = processar_lote(con, args.lote)
        con.close()

        cabecalho = montar_cabecalho(competencia, len(linhas), n_folhas, linhas)
        ok, tam   = _validar(linhas)
        icone     = "✅" if ok else "⚠️ "
        print(f"\n{icone} Validação: {len(linhas)} linha(s) de detalhe, {tam} chars cada")

        caminho = gerar_arquivo(linhas, cabecalho, competencia)
        print(f"\n✅ Arquivo: {caminho}")
        print(f"   Registros   : {len(linhas)}")
        print(f"   Folhas      : {n_folhas}")
        print(f"   Competência : {competencia[4:6]}/{competencia[:4]}")
        return

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
    cabecalho        = montar_cabecalho(competencia, len(linhas), n_folhas, linhas)

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
