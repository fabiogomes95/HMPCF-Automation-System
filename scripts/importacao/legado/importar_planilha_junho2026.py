#!/usr/bin/env python3
"""
importar_planilha_junho2026.py
==============================
Importa os atendimentos manuais do dia 16/06/2026 (registros 8-125)
da planilha de recepção para o PostgreSQL.

Lógica:
  - Paciente já cadastrado (por CPF ou CNS) → apenas cria o atendimento.
  - Paciente novo                            → cadastra e cria o atendimento.
  - Endereço: "RUA, NUMERO, BAIRRO" (separado por vírgula).
  - Telefone: adiciona DDD 84 antes do número.
  - Data do atendimento: 2026-06-16 + horário da coluna.

ARQUIVADO (script one-off, já executado) — mantido só como referência
histórica de como uma importação manual pontual foi feita. Movido de
scripts/importacao/ para scripts/importacao/legado/ em 04/09/2026; os
caminhos relativos abaixo já foram ajustados para a nova localização.
"""

import csv
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Carrega .env do projeto se existir
_ENV = Path(__file__).parent.parent.parent / ".env"
if not _ENV.exists():
    _ENV = Path(__file__).parent.parent / ".env"
if _ENV.exists():
    for _line in _ENV.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    import psycopg2.errors
except ImportError:
    print("ERRO: psycopg2 não instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

# ── Configuração ───────────────────────────────────────────────────────────────
PG = dict(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    dbname=os.getenv("POSTGRES_DB", "hmpcf"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", ""),
)

PLANILHA    = Path(__file__).parent.parent.parent.parent / "PLANILHA 2026 RECEP - JUNHO 2026.csv"
DATA_BASE   = "2026-06-16"
TZ_BR       = timezone(timedelta(hours=-3))

CORES_VALIDAS = {
    "BRANCA", "BRANCO", "PRETA", "PRETO",
    "PARDA",  "PARDO",  "AMARELA", "AMARELO",
    "INDIGENA", "INDÍGENA", "INDIO", "ÍNDIO",
}
RACA_MAP = {
    "BRANCA": "01", "BRANCO": "01",
    "PRETA":  "02", "PRETO":  "02",
    "PARDA":  "03", "PARDO":  "03",
    "AMARELA":"04", "AMARELO":"04",
    "INDIGENA":"05","INDÍGENA":"05",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def so_digitos(v: object) -> str:
    return re.sub(r"\D", "", str(v or ""))


def validar_cpf(cpf: str) -> bool:
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


def validar_cns(cns: str) -> bool:
    d = so_digitos(cns)
    if len(d) != 15 or d[0] not in "12789":
        return False
    return sum(int(d[i]) * (15 - i) for i in range(15)) % 11 == 0


def parse_dtnasc(raw: str):
    """Converte DD/MM/YYYY (ou variações) → YYYYMMDD."""
    raw = str(raw or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y",):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    # Tenta com componentes soltos (ex: 27/1/1984)
    parts = re.split(r"[/\-]", raw)
    if len(parts) == 3:
        try:
            d, m, y = parts
            return datetime(int(y), int(m), int(d)).strftime("%Y%m%d")
        except Exception:
            pass
    return None


def parse_endereco(raw: str):
    """
    'RUA, NUMERO, BAIRRO' → (logpcn, numpcn, bairro_pcnte).
    Sem vírgulas → tudo vai para logpcn.
    """
    raw = str(raw or "").strip().strip('"').strip()
    if not raw:
        return None, None, None
    parts = [p.strip() for p in raw.split(",")]
    parts = [p for p in parts if p]
    if len(parts) >= 3:
        return parts[0], parts[1], ", ".join(parts[2:])
    if len(parts) == 2:
        return parts[0], parts[1], None
    return parts[0] if parts else None, None, None


def parse_tel(raw: str):
    """
    Adiciona DDD 84. Retorna (ddtel, tel) ou (None, None).
    tel_pcnte é String(9) — limita a 9 dígitos.
    """
    raw = str(raw or "").strip()
    if not raw or raw in ("-", ""):
        return None, None
    digitos = so_digitos(raw)
    if not digitos or len(digitos) < 4:
        return None, None
    tel = digitos[:9] if len(digitos) >= 9 else digitos
    return "84", tel


def parse_row(row: list) -> dict:
    """
    Extrai todos os campos de uma linha CSV.
    Detecta automaticamente se o campo 'cor/raça' está ausente
    (quando isso ocorre, as colunas ficam deslocadas em 1 posição a partir da col 5).
    """
    n = len(row)

    cor_candidata = row[5].strip().upper() if n > 5 else ""
    # Se col 5 não é uma cor conhecida, assume que o campo foi omitido
    col_shifted = bool(cor_candidata) and cor_candidata not in CORES_VALIDAS

    if col_shifted:
        cor     = "PARDA"          # padrão quando omitido
        cidade  = row[5].strip() if n > 5 else ""
        horario = row[6].strip() if n > 6 else ""
        cpf_raw = row[7].strip() if n > 7 else ""
        sus_raw = row[8].strip() if n > 8 else ""
        # col 9 = separador vazio
        end_parts = [
            row[10].strip() if n > 10 else "",
            row[11].strip() if n > 11 else "",
        ]
        end_raw = ", ".join(p for p in end_parts if p)
        tel_raw = row[12].strip() if n > 12 else ""
    else:
        cor     = cor_candidata
        cidade  = row[6].strip()  if n > 6  else ""
        horario = row[7].strip()  if n > 7  else ""
        cpf_raw = row[8].strip()  if n > 8  else ""
        sus_raw = row[9].strip()  if n > 9  else ""
        # col 10 = separador vazio
        end_raw = row[11].strip() if n > 11 else ""
        tel_raw = row[12].strip() if n > 12 else ""

    return dict(
        registro = row[0].strip() if n > 0 else "",
        nome     = row[1].strip().upper() if n > 1 else "",
        dn_raw   = row[2].strip() if n > 2 else "",
        sexo     = row[4].strip().upper() if n > 4 else "",
        cor      = cor,
        cidade   = cidade,
        horario  = horario,
        cpf_raw  = cpf_raw,
        sus_raw  = sus_raw,
        end_raw  = end_raw,
        tel_raw  = tel_raw,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not PLANILHA.exists():
        print(f"ERRO: planilha não encontrada em {PLANILHA}")
        sys.exit(1)

    conn = psycopg2.connect(**PG)
    cur  = conn.cursor(cursor_factory=DictCursor)

    stats = dict(pac_inseridos=0, pac_existentes=0, pac_erro=0,
                 atend_ok=0, atend_erro=0)
    erros   = []
    ok_list = []

    with open(PLANILHA, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # pula cabeçalho

        for linha_num, row in enumerate(reader, start=2):
            if not row or not row[0].strip():
                continue

            d = parse_row(row)

            try:
                reg_int = int(d["registro"])
            except ValueError:
                continue

            nome = d["nome"]
            if len(nome) < 3:
                erros.append(f"Reg {reg_int}: nome inválido: '{nome}'")
                stats["pac_erro"] += 1
                continue

            dtnasc = parse_dtnasc(d["dn_raw"])
            sexo   = d["sexo"] if d["sexo"] in ("M", "F") else None
            raca   = RACA_MAP.get(d["cor"].upper(), "03")

            cpf_dig = so_digitos(d["cpf_raw"])
            cpf     = cpf_dig if cpf_dig and validar_cpf(cpf_dig) else None

            cns_dig = so_digitos(d["sus_raw"])
            cns     = cns_dig if cns_dig and len(cns_dig) == 15 and validar_cns(cns_dig) else None

            if not cpf and not cns:
                erros.append(
                    f"Reg {reg_int} ({nome}): sem CPF/CNS válido "
                    f"(cpf={d['cpf_raw']!r}, sus={d['sus_raw']!r})"
                )
                stats["pac_erro"] += 1
                continue

            logpcn, numpcn, bairro = parse_endereco(d["end_raw"])
            ddtel, tel             = parse_tel(d["tel_raw"])

            # ── Buscar paciente existente ──────────────────────────────────────
            paciente_id = None

            if cpf:
                cur.execute("SELECT id FROM pacientes WHERE num_cpf = %s", (cpf,))
                r = cur.fetchone()
                if r:
                    paciente_id = r["id"]

            if not paciente_id and cns:
                cur.execute("SELECT id FROM pacientes WHERE cns = %s", (cns,))
                r = cur.fetchone()
                if r:
                    paciente_id = r["id"]

            if paciente_id:
                stats["pac_existentes"] += 1
            else:
                # ── Inserir novo paciente ──────────────────────────────────────
                try:
                    cur.execute(
                        """
                        INSERT INTO pacientes (
                            num_cpf, cns, nome, dtnasc, sexo, raca,
                            logpcn, numpcn, bairro_pcnte,
                            ddtel_pcnte, tel_pcnte, cidade,
                            ibge, ceppcn, co_lograd, nacionalidade
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            '240360', '59575000', '081', '010'
                        )
                        RETURNING id
                        """,
                        (cpf, cns, nome, dtnasc, sexo, raca,
                         logpcn, numpcn, bairro,
                         ddtel, tel, d["cidade"]),
                    )
                    paciente_id = cur.fetchone()["id"]
                    conn.commit()
                    stats["pac_inseridos"] += 1

                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    # Outro processo pode ter inserido no meio — tentar recuperar
                    if cpf:
                        cur.execute("SELECT id FROM pacientes WHERE num_cpf = %s", (cpf,))
                        r = cur.fetchone()
                        if r:
                            paciente_id = r["id"]
                    if not paciente_id and cns:
                        cur.execute("SELECT id FROM pacientes WHERE cns = %s", (cns,))
                        r = cur.fetchone()
                        if r:
                            paciente_id = r["id"]
                    if paciente_id:
                        stats["pac_existentes"] += 1
                    else:
                        erros.append(f"Reg {reg_int} ({nome}): UniqueViolation mas paciente não localizado após rollback")
                        stats["pac_erro"] += 1
                        continue

                except Exception as e:
                    conn.rollback()
                    erros.append(f"Reg {reg_int} ({nome}): ERRO ao inserir paciente — {e}")
                    stats["pac_erro"] += 1
                    continue

            # ── Criar atendimento ──────────────────────────────────────────────
            try:
                horario_str = d["horario"]
                if horario_str:
                    try:
                        dt_atend = datetime.strptime(
                            f"{DATA_BASE} {horario_str}", "%Y-%m-%d %H:%M"
                        )
                    except ValueError:
                        dt_atend = datetime.strptime(DATA_BASE, "%Y-%m-%d")
                else:
                    dt_atend = datetime.strptime(DATA_BASE, "%Y-%m-%d")

                dt_atend = dt_atend.replace(tzinfo=TZ_BR)

                cur.execute(
                    """
                    INSERT INTO recepcao_atendimentos (paciente_id, data_atendimento, registro)
                    VALUES (%s, %s, %s)
                    """,
                    (paciente_id, dt_atend, reg_int),
                )
                conn.commit()
                stats["atend_ok"] += 1
                ok_list.append(f"  Reg {reg_int:>3} | {nome:<45} | pac_id={paciente_id}")

            except Exception as e:
                conn.rollback()
                erros.append(f"Reg {reg_int} ({nome}): ERRO ao criar atendimento — {e}")
                stats["atend_erro"] += 1

    cur.close()
    conn.close()

    # ── Relatório ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RESULTADO DA IMPORTAÇÃO — JUNHO 2026")
    print("=" * 60)
    print(f"  Pacientes novos inseridos : {stats['pac_inseridos']}")
    print(f"  Pacientes já existentes   : {stats['pac_existentes']}")
    print(f"  Erros de paciente         : {stats['pac_erro']}")
    print(f"  Atendimentos criados      : {stats['atend_ok']}")
    print(f"  Erros de atendimento      : {stats['atend_erro']}")
    print("=" * 60)

    if ok_list:
        print(f"\n{'─'*60}")
        print("  ATENDIMENTOS CRIADOS:")
        print(f"{'─'*60}")
        for line in ok_list:
            print(line)

    if erros:
        print(f"\n{'─'*60}")
        print(f"  ERROS ({len(erros)}):")
        print(f"{'─'*60}")
        for e in erros:
            print(f"  ► {e}")
    else:
        print("\n  ✓ Nenhum erro encontrado.")


if __name__ == "__main__":
    main()
