"""
Importação de planilhas manuais de recepção (.tsv) para o PostgreSQL.

Formato esperado (13 colunas, separadas por TAB):
  registro | nome | data_nasc (DD/MM/AAAA) | idade | sexo | cor | cidade |
  horário | cpf | cns | (vazio) | endereço ("RUA , NUMERO-BAIRRO") | telefone

Linhas de cabeçalho de dia contêm uma data no formato DD/MM/AAAA em qualquer
lugar da linha (ex: "01/06/2026" ou "PLANTAO DIURNO - 02/06/2026 - ...").
"""
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

TZ_BR = timezone(timedelta(hours=-3))

RACA_MAP = {
    "BRANCA": "01", "BRANCO": "01",
    "PRETA": "02", "PRETO": "02",
    "PARDA": "03", "PARDO": "03",
    "AMARELA": "04", "AMARELO": "04",
    "INDIGENA": "05", "INDÍGENA": "05",
}

_DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")


def so_digitos(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def validar_cpf(cpf) -> bool:
    d = so_digitos(cpf)
    if len(d) != 11 or re.match(r"^(\d)\1{10}$", d):
        return False
    soma = sum(int(d[i]) * (10 - i) for i in range(9))
    r = soma % 11
    dig1 = 0 if r < 2 else 11 - r
    if dig1 != int(d[9]):
        return False
    soma = sum(int(d[i]) * (11 - i) for i in range(10))
    r = soma % 11
    dig2 = 0 if r < 2 else 11 - r
    return dig2 == int(d[10])


def validar_cns(cns) -> bool:
    d = so_digitos(cns)
    if len(d) != 15 or d[0] not in "12789":
        return False
    return sum(int(d[i]) * (15 - i) for i in range(15)) % 11 == 0


def parse_dtnasc(raw) -> str | None:
    raw = str(raw or "").strip()
    parts = re.split(r"[/\-]", raw)
    if len(parts) == 3:
        try:
            d, m, y = parts
            return f"{int(y):04d}{int(m):02d}{int(d):02d}"
        except ValueError:
            return None
    return None


def parse_endereco(raw) -> tuple[str | None, str | None, str | None]:
    raw = str(raw or "").strip()
    if not raw:
        return None, None, None
    if "," not in raw:
        return raw or None, None, None
    rua, resto = raw.split(",", 1)
    rua, resto = rua.strip(), resto.strip()
    if "-" in resto:
        numero, bairro = resto.split("-", 1)
        return rua or None, numero.strip() or None, bairro.strip() or None
    return rua or None, resto or None, None


def parse_tel(raw) -> tuple[str | None, str | None]:
    raw = str(raw or "").strip()
    if not raw or raw == "-":
        return None, None
    digitos = so_digitos(raw)
    if not digitos or len(digitos) < 4:
        return None, None
    tel = digitos[:9] if len(digitos) >= 9 else digitos
    return "84", tel


def parse_horario(raw) -> tuple[int, int] | None:
    raw = str(raw or "").strip()
    m = re.match(r"^(\d{1,2})[:;.,](\d{2})", raw)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return (h, mi) if 0 <= h <= 23 and 0 <= mi <= 59 else None


_INICIO_DIURNO_HORA = 7  # plantão diurno costuma começar às 07:00


def parsear_tsv(conteudo: str) -> tuple[list[dict], list[str]]:
    """Extrai todos os registros de paciente de um TSV de recepção.

    Cada dia tem um cabeçalho "PLANTÃO DIURNO ..." e um "PLANTÃO NOTURNO ...".
    O plantão noturno cruza a meia-noite — atendimentos de madrugada (antes das
    07h) sob esse cabeçalho são, na prática, gravados no sistema com a data do
    dia SEGUINTE (confirmado contra dados reais). O ano do cabeçalho também é
    corrigido automaticamente caso destoe do mês/ano predominante no arquivo
    (erro de digitação comum, ex: "2016" em vez de "2026").

    Retorna (registros, linhas_ignoradas) — linhas_ignoradas são linhas que não
    são cabeçalho de dia nem uma linha de paciente reconhecível (ex: erro de
    digitação na planilha), para revisão manual.
    """
    registros = []
    ignoradas = []
    current_date: date | None = None
    current_turno = "DIURNO"
    mes_ano_base: tuple[int, int] | None = None

    for raw in conteudo.splitlines():
        if not raw.strip():
            continue
        cols = raw.split("\t")
        primeiro = cols[0].strip()

        m = _DATE_RE.search(raw)
        is_cabecalho_dia = bool(m) and (primeiro == m.group(1) or "PLANT" in raw.upper())
        if is_cabecalho_dia:
            d, mo, y = (int(x) for x in m.group(1).split("/"))
            if mes_ano_base is None:
                mes_ano_base = (mo, y)
            elif (mo, y) != mes_ano_base:
                mo, y = mes_ano_base  # corrige erro de digitação no ano/mês do cabeçalho
            current_date = date(y, mo, d)
            current_turno = "NOTURNO" if "NOTURNO" in raw.upper() else "DIURNO"
            continue

        if not primeiro.isdigit() or len(cols) < 13:
            ignoradas.append(raw)
            continue

        nome = cols[1].strip().upper()
        if not nome or current_date is None:
            continue

        horario_raw = cols[7].strip()
        hora = parse_horario(horario_raw)

        dia_efetivo = current_date
        if hora and current_turno == "NOTURNO" and hora[0] < _INICIO_DIURNO_HORA:
            dia_efetivo = current_date + timedelta(days=1)

        cpf_dig = so_digitos(cols[8])
        cpf = cpf_dig if cpf_dig and validar_cpf(cpf_dig) else None
        cns_dig = so_digitos(cols[9])
        cns = cns_dig if cns_dig and len(cns_dig) == 15 and validar_cns(cns_dig) else None
        logpcn, numpcn, bairro = parse_endereco(cols[11])
        ddtel, tel = parse_tel(cols[12])

        registros.append({
            "dia": dia_efetivo,
            "registro": int(primeiro),
            "nome": nome,
            "cpf": cpf,
            "cns": cns,
            "dtnasc": parse_dtnasc(cols[2]),
            "sexo": cols[4].strip().upper() if cols[4].strip().upper() in ("M", "F") else None,
            "raca": RACA_MAP.get(cols[5].strip().upper(), "03"),
            "cidade": cols[6].strip() or None,
            "logpcn": logpcn,
            "numpcn": numpcn,
            "bairro": bairro,
            "ddtel": ddtel,
            "tel": tel,
            "hora": hora,
            "horario_raw": horario_raw,
        })

    return registros, ignoradas


def comparar_com_banco(engine, registros: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Retorna (faltando, sem_documento, sem_horario)."""
    sem_doc = [r for r in registros if not r["cpf"] and not r["cns"]]
    sem_hora = [r for r in registros if not r["hora"] and (r["cpf"] or r["cns"])]
    verificaveis = [r for r in registros if r["hora"] and (r["cpf"] or r["cns"]) and r["dia"]]

    faltando = []
    with engine.connect() as conn:
        for r in verificaveis:
            dia = r["dia"]
            row = conn.execute(text("""
                SELECT 1
                FROM recepcao_atendimentos rt
                JOIN pacientes p ON p.id = rt.paciente_id
                WHERE rt.data_atendimento::date = :dia
                  AND ((:cpf IS NOT NULL AND p.num_cpf = :cpf) OR (:cns IS NOT NULL AND p.cns = :cns))
                LIMIT 1
            """), {"dia": dia, "cpf": r["cpf"], "cns": r["cns"]}).fetchone()
            if not row:
                faltando.append(r)

    return faltando, sem_doc, sem_hora


def importar_faltantes(engine, faltando: list[dict]) -> dict:
    """Insere pacientes (se necessário) e atendimentos para os registros faltantes."""
    stats = {"pacientes_novos": 0, "pacientes_existentes": 0, "atendimentos_criados": 0, "erros": []}

    with engine.connect() as conn:
        for r in faltando:
            try:
                existe = conn.execute(text(
                    "SELECT id FROM pacientes WHERE (:cpf IS NOT NULL AND num_cpf = :cpf) "
                    "OR (:cns IS NOT NULL AND cns = :cns)"
                ), {"cpf": r["cpf"], "cns": r["cns"]}).fetchone()

                if existe:
                    paciente_id = existe[0]
                    stats["pacientes_existentes"] += 1
                else:
                    novo = conn.execute(text("""
                        INSERT INTO pacientes (
                            num_cpf, cns, nome, dtnasc, sexo, raca,
                            logpcn, numpcn, bairro_pcnte,
                            ddtel_pcnte, tel_pcnte, cidade,
                            ibge, ceppcn, co_lograd, nacionalidade
                        ) VALUES (
                            :cpf, :cns, :nome, :dtnasc, :sexo, :raca,
                            :logpcn, :numpcn, :bairro,
                            :ddtel, :tel, :cidade,
                            '240360', '59575000', '081', '010'
                        ) RETURNING id
                    """), r)
                    paciente_id = novo.fetchone()[0]
                    stats["pacientes_novos"] += 1

                dia = r["dia"]
                h, mi = r["hora"]
                dt_atend = datetime(dia.year, dia.month, dia.day, h, mi, tzinfo=TZ_BR)

                conn.execute(text("""
                    INSERT INTO recepcao_atendimentos (paciente_id, data_atendimento, registro)
                    VALUES (:pid, :dt, :reg)
                """), {"pid": paciente_id, "dt": dt_atend, "reg": r["registro"]})

                conn.commit()
                stats["atendimentos_criados"] += 1

            except Exception as e:
                conn.rollback()
                stats["erros"].append(f"Reg {r['registro']} ({r['nome']}, {r['dia']}): {e}")

    return stats
