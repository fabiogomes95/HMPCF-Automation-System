"""
Núcleo da geração do arquivo BPA-I (CNES 2409283) — layout DATASUS,
350 caracteres por linha de detalhe, 130 no cabeçalho, encoding latin-1, CRLF.

Validado em 2026-06-18 byte a byte contra o layout oficial DATASUS
(C:/BPA/Layout_Exportacao_BPA.pdf) e um arquivo .MAR já exportado pelo BPA
Magnético em produção (checksum do cabeçalho reproduzido com sucesso).

Processo 100% independente — não importa nada do backend/ (Recepção) nem
do frontend/. Usa as próprias credenciais em dashboard/.env.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import firebirdsql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

FIREBIRD_PATH     = os.getenv("FIREBIRD_PATH", r"C:\BPA\BPAMAG.GDB")
FIREBIRD_USER     = os.getenv("FIREBIRD_USER", "SYSDBA")
FIREBIRD_PASSWORD = os.getenv("FIREBIRD_PASSWORD", "masterkey")
BPA_LOTES_DIR     = os.getenv("BPA_LOTES_DIR", str(BASE_DIR / "bpa_lotes"))
BPA_SAIDA_DIR      = os.getenv("BPA_SAIDA_DIR")  # se vazio, usa ~/Downloads

# ── Configurações fixas da unidade ──────────────────────────────────────────
# ORGAO_RESP, SIGLA_ORGAO, CNPJ_PRESTADOR, ORGAO_DEST e DESTINO_INDICADOR
# copiados literalmente do cabeçalho de um export real já aceito em produção,
# para garantir compatibilidade exata.
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


class LoteError(Exception):
    """Erro de domínio ao processar um lote BPA (arquivo ausente/vazio/inválido)."""


# ── Triagem: validação de CNS/CPF (dígito verificador real) ─────────────────
def valida_cns(cns: str) -> bool:
    if not cns or len(cns) != 15 or cns[0] not in "12789":
        return False
    if cns[0] in "789":
        return sum(int(cns[i]) * (15 - i) for i in range(15)) % 11 == 0
    pis = cns[:11]
    soma = sum(int(pis[i]) * (15 - i) for i in range(11))
    resto = soma % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    if dv == 10:
        soma += 2
        resto = soma % 11
        dv = 11 - resto
        resultado = pis + "001" + str(dv)
    else:
        resultado = pis + "000" + str(dv)
    return cns == resultado


def valida_cpf(cpf: str) -> bool:
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]


def extrair_documentos_validos(texto_sujo: str) -> list[str]:
    """
    Varre um texto "sujo" linha a linha, extrai o primeiro CPF válido de
    cada linha e remove repetições consecutivas (digitação dupla acidental).

    Desde a atualização do BPA, o paciente é identificado APENAS por CPF;
    números de SUS/CNS são ignorados na triagem (ver valida_cns, mantida
    só para uso histórico).
    """
    resultado = []
    ultimo = None
    for linha in (texto_sujo or "").splitlines():
        if not linha.strip():
            continue
        cpf_encontrado = ""
        for token in linha.split():
            num = "".join(c for c in token if c.isdigit())
            if len(num) == 11 and valida_cpf(num):
                cpf_encontrado = num
        if cpf_encontrado and cpf_encontrado != ultimo:
            ultimo = cpf_encontrado
            resultado.append(cpf_encontrado)
    return resultado


def dividir_em_lotes(documentos: list[str], profissionais: list[str], data_br: str) -> str:
    """
    Divide a lista de documentos em blocos de até 99 (limite do BPA por
    folha), distribuindo entre os profissionais informados em rodízio
    (round-robin), no formato "PROFISSIONAL: X | DATA: Y".
    """
    nomes = [p.strip().upper() for p in profissionais if p.strip()] or ["PROFISSIONAL SEM NOME"]
    TAMANHO_LOTE = 99
    blocos = []
    idx_prof = 0
    for i in range(0, len(documentos), TAMANHO_LOTE):
        chunk = documentos[i:i + TAMANHO_LOTE]
        prof_atual = nomes[idx_prof % len(nomes)]
        idx_prof += 1
        blocos.append(f"PROFISSIONAL: {prof_atual} | DATA: {data_br}")
        blocos.extend(chunk)
        blocos.append("")
    return "\n".join(blocos)


def nome_arquivo_lote(data_br: str) -> str:
    """'16/04/2026' → '16-04-2026.txt' — mesmo arquivo do dia para Digitação/Triagem/Geração."""
    return f"{(data_br or '').replace('/', '-')}.txt"


# ── Conexão Firebird ─────────────────────────────────────────────────────────
def conectar():
    return firebirdsql.connect(
        host="localhost",
        database=FIREBIRD_PATH,
        user=FIREBIRD_USER,
        password=FIREBIRD_PASSWORD,
        charset="WIN1252",
    )


# ── Cache de pacientes (CADCNS) para busca em tempo real na Digitação ──────
def carregar_pacientes_cadcns() -> list[dict]:
    """Carrega CNS/NOME/DTNASC/CPF de toda a CADCNS — usado pela busca instantânea."""
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS")
        pacientes = []
        for cns, nome, dtnasc, cpf in cur.fetchall():
            dn_raw = str(dtnasc or "").strip()
            dtnasc_fmt = f"{dn_raw[6:8]}/{dn_raw[4:6]}/{dn_raw[0:4]}" if len(dn_raw) == 8 else ""
            pacientes.append({
                "sus": str(cns or "").strip(),
                "nome": str(nome or "").strip().upper(),
                "dtnasc": dtnasc_fmt,
                "cpf": str(cpf or "").strip(),
            })
        return pacientes
    finally:
        con.close()


def buscar_pacientes_memoria(termo: str, base_pacientes: list[dict], limite: int = 50) -> list[dict]:
    """Busca por nome, SUS ou CPF na lista já carregada na memória (instantâneo).

    A busca aceita SUS para localizar o paciente, mas o documento gravado no
    lote deve ser sempre o CPF (responsabilidade do chamador).
    """
    if not termo:
        return base_pacientes[:limite]
    termo = termo.upper().strip()
    resultados = []
    for p in base_pacientes:
        if termo in p["nome"] or termo in p["sus"] or termo in p["cpf"]:
            resultados.append(p)
            if len(resultados) == limite:
                break
    return resultados


# ── Leitura do arquivo de lote ───────────────────────────────────────────────
def ler_arquivo_lote(caminho_arquivo: str) -> list[dict]:
    """
    Lê um arquivo no formato:
        PROFISSIONAL: <nome> | DATA: DD/MM/AAAA
        <CNS ou CPF>
        <CNS ou CPF>
        PROFISSIONAL: <outro nome> | DATA: DD/MM/AAAA
        ...

    O mesmo profissional pode aparecer em mais de um bloco no mesmo dia —
    os documentos são agrupados por (nome, data), preservando ordem e
    repetições (o mesmo paciente pode ter mais de um atendimento no dia).

    Retorna: [{"medico_raw": str, "data": "DD/MM/AAAA", "documentos": [...]}]
    """
    if not os.path.exists(caminho_arquivo):
        raise LoteError(f"Arquivo não encontrado: {caminho_arquivo}")

    with open(caminho_arquivo, encoding="utf-8") as f:
        linhas_arquivo = f.readlines()

    grupos: dict[tuple[str, str], dict] = {}
    ordem: list[tuple[str, str]] = []
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
        raise LoteError(
            f"Nenhum bloco 'PROFISSIONAL: ... | DATA: ...' encontrado em '{caminho_arquivo}'."
        )

    return [grupos[chave] for chave in ordem]


# ── Profissionais ────────────────────────────────────────────────────────────
def listar_profissionais(con) -> list[tuple[str, str]]:
    """Retorna [(cns_raw, nome), ...] de todos os profissionais cadastrados."""
    cur = con.cursor()
    cur.execute("SELECT CADMED_CNS, CADMED_NOME FROM CADMED ORDER BY CADMED_NOME")
    rows = cur.fetchall()
    return [(str(cns).strip(), str(nome).strip()) for cns, nome in rows]


def mapa_categorias_por_profissional(con) -> dict[str, set[str]]:
    """Retorna {cns_raw: {"medico", "enfermeiro", ...}} via CADMED_CBO_CNES."""
    cur = con.cursor()
    cur.execute("SELECT MED_CNS, MED_CBO FROM CADMED_CBO_CNES")
    mapa: dict[str, set[str]] = {}
    for cns, cbo in cur.fetchall():
        categoria = CBO_PARA_CATEGORIA.get(str(cbo).strip())
        if categoria:
            mapa.setdefault(str(cns).strip(), set()).add(categoria)
    return mapa


def detectar_categoria(con, cns_prof_raw: str) -> tuple[str | list[str], bool]:
    """
    Detecta médico/enfermeiro via CADMED_CBO_CNES.
    Retorna (categoria, automatico=True) se exatamente 1 CBO conhecido.
    Caso contrário, (lista_de_categorias_possiveis, False) — lista vazia
    se nenhum CBO conhecido estiver cadastrado.
    """
    cur = con.cursor()
    cur.execute("SELECT MED_CBO FROM CADMED_CBO_CNES WHERE MED_CNS = ?", (cns_prof_raw,))
    cbos_cadastrados   = {str(r[0]).strip() for r in cur.fetchall()}
    categorias_validas = sorted({CBO_PARA_CATEGORIA[c] for c in cbos_cadastrados if c in CBO_PARA_CATEGORIA})

    if len(categorias_validas) == 1:
        return categorias_validas[0], True
    return categorias_validas, False


def resolver_profissional_por_nome(profissionais: list[tuple[str, str]], nome_raw: str) -> dict:
    """
    Tenta achar o profissional pelo nome (como vem do arquivo de lote, ex.
    "RAFHAELA LOPES" ou só "STELA") comparando tokens contra o nome cadastrado.
    Todo token do nome_raw precisa aparecer como palavra inteira no nome
    cadastrado (evita falso-positivo tipo "STELA" casar com "ESTELA").

    Retorna dict:
      {"status": "auto", "cns": ..., "nome": ...}                         — achou exatamente 1
      {"status": "ambiguo", "candidatos": [(cns, nome), ...]}             — achou mais de 1
      {"status": "nao_encontrado", "candidatos": <profissionais inteiro>} — não achou nenhum
    """
    tokens = nome_raw.upper().split()
    candidatos = [
        (cns, nome) for cns, nome in profissionais
        if all(tok in nome.upper().split() for tok in tokens)
    ]

    if len(candidatos) == 1:
        cns_raw, nome = candidatos[0]
        return {"status": "auto", "cns": cns_raw, "nome": nome}
    if candidatos:
        return {"status": "ambiguo", "candidatos": candidatos}
    return {"status": "nao_encontrado", "candidatos": profissionais}


# ── Busca de pacientes (geração) ─────────────────────────────────────────────
def _normalizar_dtnasc(valor) -> str:
    """Normaliza DTNASC para string AAAAMMDD (CADCNS já guarda nesse formato)."""
    if valor is None:
        return "19000101"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%Y%m%d")
    s = str(valor).strip().replace("/", "").replace("-", "")
    return s[:8] if len(s) >= 8 else "19000101"


def _buscar_dados_pacientes(con, cns_list: list[str], cpf_list: list[str]) -> dict[str, dict]:
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

    por_documento: dict[str, dict] = {}
    for row in cur.fetchall():
        cns_raw = str(row[0]).strip() if row[0] else ""
        cns     = cns_raw.zfill(15) if cns_raw else " " * 15
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


def buscar_pacientes(con, lista_valores: list[str]) -> tuple[list[dict], list[str], list[str]]:
    """
    Busca os pacientes cujo CNS (15 dígitos) ou CPF (11 dígitos, coluna
    NUM_CPF) está na lista de entrada.

    Retorna (pacientes, nao_encontrados, invalidos):
      - pacientes na MESMA ORDEM e com as MESMAS REPETIÇÕES da entrada
        (cada ocorrência representa um atendimento distinto — o mesmo
        paciente pode ter mais de um atendimento no dia, não é deduplicado).
      - nao_encontrados: documentos válidos (CNS-15/CPF-11) não achados na CADCNS.
      - invalidos: valores com tamanho que não é nem CNS nem CPF.
    """
    cns_list  = [v for v in lista_valores if len(v) == 15]
    cpf_list  = [v for v in lista_valores if len(v) == 11]
    invalidos = [v for v in lista_valores if v not in cns_list and v not in cpf_list]

    por_documento = _buscar_dados_pacientes(con, cns_list, cpf_list)

    pacientes       = []
    nao_encontrados = []
    for v in lista_valores:
        if v in invalidos:
            continue
        dados = por_documento.get(v)
        if dados:
            pacientes.append(dados)
        elif v not in nao_encontrados:
            nao_encontrados.append(v)

    return pacientes, nao_encontrados, invalidos


# ── Montagem do layout BPA-I ─────────────────────────────────────────────────
def _calcular_idade(nasc_str: str, ref: date) -> int:
    try:
        d = date(int(nasc_str[:4]), int(nasc_str[4:6]), int(nasc_str[6:8]))
        return ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))
    except Exception:
        return 0


def _linha_detalhe(pac, proc, cbo, cns_prof, data_aten, competencia, folha, seq) -> str:
    """Layout BPA-I oficial (350 chars) — ver docstring do módulo."""
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
        + pac["cns"]                                   # 015 | prd-cnspac
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


def montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia) -> tuple[list[str], int]:
    linhas = []
    folha  = 1
    seq    = 1
    for pac in pacientes:
        if seq > 99:
            seq = 1
            folha += 1
        linhas.append(_linha_detalhe(pac, proc, cbo, cns_prof, data_aten, competencia, folha, seq))
        seq += 1
    return linhas, folha


def _calcular_checksum(linhas: list[str]) -> str:
    """
    cbc-smt-vrf: soma do código do procedimento (prd-pa) + quantidade
    (prd-qt) de cada linha, resto da divisão por 1111, + 1111. Lê os valores
    direto das linhas já montadas (posições 49-59 e 88-94), então funciona
    mesmo com procedimentos diferentes misturados (médico + enfermeiro).
    """
    total = sum(int(l[49:59]) + int(l[88:94]) for l in linhas)
    return str(total % 1111 + 1111).zfill(4)


def montar_cabecalho(competencia: str, n_linhas: int, n_folhas: int, linhas: list[str]) -> str:
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


def validar(linhas: list[str]) -> tuple[bool, int]:
    if not linhas:
        return True, 0
    tam   = len(linhas[0])
    erros = any(len(l) != tam for l in linhas)
    return not erros, tam


def gerar_arquivo(linhas: list[str], cabecalho: str, competencia: str, pasta: str | None = None) -> str:
    pasta = pasta or BPA_SAIDA_DIR or os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(pasta, exist_ok=True)
    nome  = os.path.join(pasta, f"BPAI_{CNES}_{competencia}.txt")
    # newline="" garante CRLF real sem duplicação em qualquer plataforma
    with open(nome, "w", encoding="latin-1", newline="") as f:
        f.write(cabecalho + "\r\n")
        for linha in linhas:
            f.write(linha + "\r\n")
    return nome


# ── Lotes (.txt) ──────────────────────────────────────────────────────────────
def garantir_pasta_lotes() -> str:
    os.makedirs(BPA_LOTES_DIR, exist_ok=True)
    return BPA_LOTES_DIR


def caminho_lote(nome_arquivo: str) -> str:
    pasta = garantir_pasta_lotes()
    return os.path.join(pasta, nome_arquivo)


def listar_lotes() -> list[dict]:
    pasta = garantir_pasta_lotes()
    arquivos = []
    for nome in os.listdir(pasta):
        if not nome.lower().endswith(".txt"):
            continue
        caminho = os.path.join(pasta, nome)
        stat = os.stat(caminho)
        arquivos.append({
            "nome": nome,
            "tamanho": stat.st_size,
            "modificado_em": datetime.fromtimestamp(stat.st_mtime),
        })
    arquivos.sort(key=lambda a: a["nome"], reverse=True)
    return arquivos


def criar_cabecalho_lote(nome_arquivo: str, medico: str, data: str) -> None:
    caminho = caminho_lote(nome_arquivo)
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")


def adicionar_documento_lote(nome_arquivo: str, documento: str) -> None:
    """Adiciona um CNS/CPF ao bloco atual, com rollover automático de 99 por folha."""
    caminho = caminho_lote(nome_arquivo)
    doc_limpo = documento.strip().replace(".", "").replace("-", "").replace(" ", "")
    if not doc_limpo:
        raise LoteError("Documento inválido.")

    pacientes_no_lote = 0
    ultimo_cabecalho = ""
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            linhas = f.readlines()
        for linha in reversed(linhas):
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue
            if linha_limpa.upper().startswith("PROFISSIONAL:"):
                ultimo_cabecalho = linha_limpa
                break
            pacientes_no_lote += 1

    with open(caminho, "a", encoding="utf-8") as f:
        if pacientes_no_lote >= 99 and ultimo_cabecalho:
            f.write(f"\n{ultimo_cabecalho}\n")
        f.write(f"{doc_limpo}\n")
