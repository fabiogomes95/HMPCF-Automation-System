from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from app.utils import apenas_numeros, valida_cns

COD_IBGE = os.getenv("COD_IBGE", "240360")
NACIONALIDADE = os.getenv("NACIONALIDADE", "010")
RACA = os.getenv("RACA", "03")
CEP = os.getenv("CEP", "59575000")
COD_RUA = os.getenv("COD_RUA", "081")


def remove_accents(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", errors="ignore").decode("ascii")
    return texto.upper().strip()


def dn_iso(valor: str | None) -> str:
    if not valor:
        return "19900101"
    raw = valor.strip()
    iso = raw.replace("-", "").replace("/", "")
    if len(iso) == 8 and iso.isdigit() and int(iso[:4]) > 1900:
        return iso
    m = re.search(r"(\d{2})\D?(\d{2})\D?(\d{4})", raw)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    return "19900101"


def parse_endereco(endereco: str) -> tuple[str, str, str]:
    if not endereco:
        return "NAO INFORMADO", "S/N", "CENTRO"
    end = endereco.strip().upper()
    end = re.sub(r"\d{4,5}-\d{4}", "", end).strip()
    end = remove_accents(end)

    m = re.match(r"(.+?),\s*(\d+|S/N|SN)\b[\s.-]*(.*)", end)
    if m:
        return (
            m.group(1).strip().rstrip(",").strip()[:30],
            m.group(2)[:6],
            (m.group(3).strip().strip("-").strip() or "CENTRO")[:20],
        )

    matches = list(re.finditer(r"\d+|\bS/N\b|\bSN\b", end))
    if matches:
        best = matches[-1]
        return (
            end[:best.start()].strip("., -")[:30] or "NAO INFORMADO",
            best.group().strip()[:6],
            end[best.end():].strip("., -")[:20] or "CENTRO",
        )

    return end[:30], "S/N", "CENTRO"


def format_telefone(tel_raw: str) -> tuple[str, str]:
    tel = apenas_numeros(tel_raw)
    if len(tel) == 8:
        tel = "84" + tel
    elif len(tel) == 9 and tel.startswith("9"):
        tel = "84" + tel
    elif len(tel) < 10:
        tel = "84" + tel.zfill(8)
    return tel[:2], tel[2:].ljust(9, "0")[:9]


def gerar_linha_bpa(sus: str, nome: str, dn: str, sexo: str,
                    endereco: str, numero: str, bairro: str,
                    ddd: str, fone: str,
                    complemento: str = "") -> str:
    campo_sus = sus.zfill(15)[:15] if sus else " ".ljust(15)
    campo_nome = nome.ljust(30)[:30]
    campo_dn = dn.ljust(8, "0")[:8]
    campo_sexo = sexo[:1] if sexo in ("M", "F") else "F"
    campo_rua = endereco.ljust(30)[:30]
    campo_complemento = complemento.ljust(10)[:10]
    campo_num = numero.ljust(5)[:5]
    campo_bairro = bairro.ljust(30)[:30]
    campo_tel = (ddd + fone).ljust(11)[:11]
    return (
        f"{campo_sus}"
        f"{campo_nome}"
        f"{campo_dn}"
        f"{campo_sexo}"
        f"{COD_IBGE}"
        f"{NACIONALIDADE}"
        f"{RACA}"
        f"     "
        f"{CEP}"
        f"{COD_RUA}"
        f"{campo_rua}"
        f"{campo_complemento}"
        f"{campo_num}"
        f"{campo_bairro}"
        f"{campo_tel}"
        f"\r\n"
    )


def salvar_buffer(buffer: str, caminho: str, encoding: str = "cp1252") -> str:
    path = Path(caminho)
    path.write_text(buffer, encoding=encoding, newline="")
    return str(path.resolve())
