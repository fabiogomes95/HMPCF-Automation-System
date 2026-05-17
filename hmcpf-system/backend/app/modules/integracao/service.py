from __future__ import annotations

import csv
import io
import os
import re
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from logging import getLogger
from pathlib import Path

from app.core.config import settings

logger = getLogger(__name__)

# ── Constantes do Firebird ──
_ISQL_PATH = r"C:\Program Files (x86)\Firebird\Firebird_1_5\bin\isql.exe"
_FB_PATH = r"C:\BPA\BPAMAG.GDB"
_FB_USER = "SYSDBA"
_FB_PASS = "masterkey"

# ── Constantes BPA ──
CODIGO_UNIDADE = os.getenv("CODIGO_UNIDADE", "0301060029")
FOLHA_CODIGO = os.getenv("FOLHA_CODIGO", "010")
SEQ_PROFISSIONAL = os.getenv("SEQ_PROFISSIONAL", "03")
CEP_RUA = os.getenv("CEP_RUA", "59000000")


# ── HELPERS ──────────────────────────────────────────────


def _remove_accents(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", errors="ignore").decode("ascii")
    return texto.upper().strip()


def _apenas_numeros(valor: str | None) -> str:
    return re.sub(r"\D", "", str(valor)) if valor else ""


def _valida_cns(cns: str) -> bool:
    nums = _apenas_numeros(cns)
    if len(nums) != 15 or nums[0] not in "12789":
        return False
    soma = sum(int(nums[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0


def _dn_iso(valor: str | None) -> str:
    if not valor:
        return "19900101"
    valor = valor.strip().replace("-", "").replace("/", "")
    if len(valor) == 8 and valor.isdigit():
        return valor
    m = re.search(r"(\d{2})\D?(\d{2})\D?(\d{4})", valor)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    return "19900101"


def _parse_endereco(endereco: str) -> tuple[str, str, str]:
    """Extrai (rua, numero, bairro) de endereço bagunçado."""
    if not endereco:
        return "NAO INFORMADO", "S/N", "CENTRO"
    end = endereco.strip().upper()
    end = re.sub(r"\d{4,5}-\d{4}", "", end).strip()
    end = _remove_accents(end)
    rua, numero, bairro = end, "S/N", "CENTRO"
    m = re.match(r"(.+?),\s*(\d+|S/N|SN)\b\s*[.\s]*(\S.*)?", end)
    if m:
        rua = m.group(1).strip().rstrip(",").strip()
        numero = m.group(2)
        bairro = m.group(3).strip() if m.group(3) else "CENTRO"
    return rua[:30], numero[:6], bairro[:20]


def _get_hospital_db() -> Path:
    path = settings.PROJECT_ROOT.parent / "hospital.db"
    return path if path.exists() else settings.PROJECT_ROOT.parent / "hmcpf-system/database/data/hospital.db"


def _get_legacy_conn() -> sqlite3.Connection:
    db_path = _get_hospital_db()
    if not db_path.exists():
        raise FileNotFoundError(f"hospital.db nao encontrado: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _isql_query(sql: str) -> str:
    """Executa SQL no Firebird via isql e retorna stdout."""
    if not os.path.exists(_ISQL_PATH) or not os.path.exists(_FB_PATH):
        return ""
    sql_file = os.path.join(tempfile.gettempdir(), "fb_integracao.txt")
    try:
        with open(sql_file, "w", encoding="ascii") as f:
            f.write(sql)
        resultado = subprocess.run(
            [_ISQL_PATH, "-q", _FB_PATH, "-u", _FB_USER, "-p", _FB_PASS, "-i", sql_file],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return resultado.stdout + resultado.stderr
    except Exception as e:
        return str(e)
    finally:
        try:
            os.remove(sql_file)
        except Exception:
            pass


# ── 1. EXPORTAR BPA (SQLite → TXT Datasus) ──────────────


def exportar_bpa(mes_ano: str = "", caminho_salvar: str = "") -> str:
    saida = io.StringIO()
    saida.write("=== EXPORTAR SQLite → TXT BPA ===\n\n")

    try:
        conn = _get_legacy_conn()
        cur = conn.cursor()
        query = "SELECT cpf, sus, nome, dn, sexo, endereco, numero, bairro, tel FROM pacientes"
        params: list[str] = []
        if mes_ano:
            query += " WHERE dn LIKE ?"
            params.append(f"%-{mes_ano[:2]}-%")
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        return f"Erro ao conectar: {e}"

    saida.write(f"Total de pacientes lidos: {len(rows)}\n\n")

    buffer = io.StringIO()
    erros: list[str] = []
    sucessos = 0
    for row in rows:
        r = dict(row)
        sus = _apenas_numeros(r.get("sus", ""))
        if len(sus) != 15 or not _valida_cns(sus):
            erros.append(f"SUS invalido: {r.get('nome','')} - {sus or r.get('sus','')}")
            continue
        nome = _remove_accents(r.get("nome", ""))[:30].ljust(30)
        dn = _dn_iso(r.get("dn", ""))
        sexo = (r.get("sexo", "") or "I")[0].upper()
        if sexo not in "MF":
            sexo = "I"
        endereco, numero, bairro = _parse_endereco(
            f"{r.get('endereco','')}, {r.get('numero','')} - {r.get('bairro','')}"
        )
        tel = _apenas_numeros(r.get("tel", ""))
        if len(tel) == 8:
            tel = "84" + tel
        elif len(tel) == 9 and tel.startswith("9"):
            tel = "84" + tel
        elif len(tel) < 10:
            tel = "84" + tel.zfill(8)
        ddd = tel[:2]
        fone = tel[2:].ljust(9, "0")[:9]

        linha = (
            f"{'HMPCF':<15}"
            f"{CODIGO_UNIDADE:<10}"
            f"{FOLHA_CODIGO:<3}"
            f"{SEQ_PROFISSIONAL:<2}"
            f"{sus:<15}"
            f"{nome}"
            f"{dn}"
            f"{sexo}"
            f"{endereco:<30}"
            f"{numero:<6}"
            f"{bairro:<20}"
            f"{CEP_RUA:<8}"
            f"BRASIL                 "
            f"84"
            f"{ddd:<2}"
            f"{fone:<9}"
            f"\r\n"
        )
        buffer.write(linha)
        sucessos += 1

    nome_arquivo = caminho_salvar or "BPA_EXPORTADO_SQLITE.txt"
    with open(nome_arquivo, "w", encoding="cp1252", newline="") as f:
        f.write(buffer.getvalue())

    saida.write(f"Registros exportados: {sucessos}\n")
    saida.write(f"Registros barrados: {len(erros)}\n")
    saida.write(f"Arquivo salvo: {os.path.abspath(nome_arquivo)}\n")

    if erros:
        nome_erro = nome_arquivo.replace(".txt", "_ERROS.txt")
        with open(nome_erro, "w", encoding="utf-8") as f:
            f.write("\n".join(erros))
        saida.write(f"Log de erros: {os.path.abspath(nome_erro)}\n")
        saida.write(f"\n--- PACIENTES BARRADOS ---\n")
        for e in erros[:20]:
            saida.write(f"  {e}\n")
        if len(erros) > 20:
            saida.write(f"  ... e mais {len(erros)-20}\n")

    return saida.getvalue()


# ── 2. IMPORTAR CSV (Smart Update) ─────────────────────


def importar_csv(separador: str = ";", caminho_csv: str = "") -> str:
    saida = io.StringIO()
    saida.write("=== IMPORTAR CSV (SMART UPDATE) ===\n\n")

    if caminho_csv:
        arquivos = [caminho_csv]
    else:
        import glob
        arquivos = glob.glob("*.csv")
        saida.write(f"CSVs encontrados: {len(arquivos)}\n")

    try:
        conn = _get_legacy_conn()
        cur = conn.cursor()
    except Exception as e:
        return f"Erro ao conectar hospital.db: {e}"

    novos = 0
    atualizados = 0
    intactos = 0
    ignorados = 0
    relatorio_novos: list[str] = []

    for arq in arquivos:
        saida.write(f"\nProcessando: {arq}\n")
        try:
            with open(arq, "r", encoding="utf-8") as f:
                linhas = list(csv.reader(f, delimiter=separador))
        except Exception:
            try:
                with open(arq, "r", encoding="latin1") as f:
                    linhas = list(csv.reader(f, delimiter=separador))
            except Exception as e:
                saida.write(f"  Erro ao ler: {e}\n")
                continue

        for i, linha in enumerate(linhas):
            if i == 0:
                continue
            if len(linha) < 2:
                continue
            nome = (linha[0] or "").strip().upper()
            dn = (linha[1] or "").strip() if len(linha) > 1 else ""
            sexo = (linha[2] or "").strip().upper() if len(linha) > 2 else ""
            cpf = _apenas_numeros(linha[3]) if len(linha) > 3 else ""
            sus = _apenas_numeros(linha[4]) if len(linha) > 4 else ""
            if not _valida_cns(sus):
                ignorados += 1
                continue
            if not nome:
                ignorados += 1
                continue
            cur.execute("SELECT cpf, nome, dn, sexo FROM pacientes WHERE sus = ?", (sus,))
            existing = cur.fetchone()
            if existing:
                ex = dict(existing)
                updates: list[str] = []
                params: list[str | None] = []
                if not ex.get("cpf") and cpf:
                    updates.append("cpf = ?")
                    params.append(cpf)
                if not ex.get("nome") and nome:
                    updates.append("nome = ?")
                    params.append(nome)
                if not ex.get("dn") and dn:
                    updates.append("dn = ?")
                    params.append(dn)
                if not ex.get("sexo") and sexo:
                    updates.append("sexo = ?")
                    params.append(sexo)
                if updates:
                    params.append(sus)
                    cur.execute(f"UPDATE pacientes SET {', '.join(updates)} WHERE sus = ?", params)
                    atualizados += 1
                else:
                    intactos += 1
            else:
                try:
                    cur.execute(
                        "INSERT INTO pacientes (nome, dn, sexo, cpf, sus) VALUES (?, ?, ?, ?, ?)",
                        (nome, dn, sexo, cpf, sus),
                    )
                    novos += 1
                    relatorio_novos.append(f"{nome} | SUS: {sus} | CPF: {cpf}")
                except Exception as e:
                    saida.write(f"  Erro inserir linha {i}: {e}\n")

    conn.commit()
    conn.close()

    saida.write(f"\n=== RESUMO ===\n")
    saida.write(f"Novos cadastros: {novos}\n")
    saida.write(f"Atualizados (parciais): {atualizados}\n")
    saida.write(f"Intactos (ja completos): {intactos}\n")
    saida.write(f"Ignorados (SUS invalido): {ignorados}\n")

    if relatorio_novos:
        nome_rel = "relatorio_importacao.txt"
        with open(nome_rel, "w", encoding="utf-8") as f:
            f.write("\n".join(relatorio_novos))
        saida.write(f"Relatorio: {os.path.abspath(nome_rel)}\n")

    return saida.getvalue()


# ── 3. CONVERTER CSV ANTIGO ─────────────────────────────


def converter_csv(caminho_csv: str = "", caminho_salvar: str = "") -> str:
    saida = io.StringIO()
    saida.write("=== CONVERTER CSV ANTIGO → TXT BPA ===\n\n")

    if not caminho_csv:
        arquivos = [a for a in os.listdir(".") if a.endswith(".csv") and a != "pacientes.csv"]
        if not arquivos:
            return "Nenhum CSV encontrado no diretorio atual."
        caminho_csv = arquivos[0]
        saida.write(f"Usando: {caminho_csv}\n")

    try:
        with open(caminho_csv, "r", encoding="utf-8") as f:
            linhas = list(csv.reader(f, delimiter=";"))
    except Exception:
        try:
            with open(caminho_csv, "r", encoding="latin1") as f:
                linhas = list(csv.reader(f, delimiter=";"))
        except Exception as e:
            return f"Erro ao ler CSV: {e}"

    saida.write(f"Linhas lidas: {len(linhas)}\n\n")

    buffer = io.StringIO()
    erros: list[str] = []
    sucessos = 0
    for i, linha in enumerate(linhas[1:], 2):
        if len(linha) < 13:
            erros.append(f"Linha {i}: colunas insuficientes ({len(linha)})")
            continue
        nome = _remove_accents(linha[1])[:30].ljust(30)
        dn = _dn_iso(linha[2])
        sexo = (linha[4] or "I")[0].upper()
        if sexo not in "MF":
            sexo = "I"
        sus = _apenas_numeros(linha[9])
        if not _valida_cns(sus):
            erros.append(f"Linha {i}: SUS invalido - {linha[9]}")
            continue
        endereco_raw = linha[11] if len(linha) > 11 else ""
        endereco, numero, bairro = _parse_endereco(endereco_raw)
        tel_raw = linha[12] if len(linha) > 12 else ""
        tel = _apenas_numeros(tel_raw)
        if len(tel) == 8:
            tel = "84" + tel
        elif len(tel) < 10:
            tel = "84" + tel.zfill(8)
        ddd = tel[:2]
        fone = tel[2:].ljust(9, "0")[:9]

        linha_txt = (
            f"{'HMPCF':<15}"
            f"{CODIGO_UNIDADE:<10}"
            f"{FOLHA_CODIGO:<3}"
            f"{SEQ_PROFISSIONAL:<2}"
            f"{sus:<15}"
            f"{nome}"
            f"{dn}"
            f"{sexo}"
            f"{endereco:<30}"
            f"{numero:<6}"
            f"{bairro:<20}"
            f"{CEP_RUA:<8}"
            f"BRASIL                 "
            f"84"
            f"{ddd:<2}"
            f"{fone:<9}"
            f"\r\n"
        )
        buffer.write(linha_txt)
        sucessos += 1

    nome_arquivo = caminho_salvar or "BPA_PLANILHA_ANTIGA.txt"
    with open(nome_arquivo, "w", encoding="cp1252", newline="") as f:
        f.write(buffer.getvalue())

    saida.write(f"Registros convertidos: {sucessos}\n")
    saida.write(f"Registros barrados: {len(erros)}\n")
    saida.write(f"Arquivo: {os.path.abspath(nome_arquivo)}\n")

    if erros:
        nome_erro = nome_arquivo.replace(".txt", "_PACIENTES_SEM_CADASTRO.txt")
        with open(nome_erro, "w", encoding="utf-8") as f:
            f.write("\n".join(erros))
        saida.write(f"Erros: {os.path.abspath(nome_erro)}\n")

    return saida.getvalue()


# ── 4. SINCRONIZAR FIREBIRD ─────────────────────────────


def sincronizar_firebird(mes_ano: str = "", caminho_salvar: str = "") -> str:
    saida = io.StringIO()
    saida.write("=== SINCRONIZAR FIREBIRD (Padronizar CADCNS) ===\n\n")

    if not os.path.exists(_ISQL_PATH):
        return "isql nao encontrado. Firebird 1.5 instalado?"

    sql = "SELECT FIRST 500 CNS, NOME, DTNASC, SEXO, NUM_CPF, LOGPCN, NUMPCN, CEPPCN, BAIRRO_PCNTE, NMRES, TEL_PCNTE, DDTEL_PCNTE FROM CADCNS ORDER BY CNS"
    sql_file = os.path.join(tempfile.gettempdir(), "fb_sync.txt")
    try:
        with open(sql_file, "w", encoding="ascii") as f:
            f.write(sql)
        resultado = subprocess.run(
            [_ISQL_PATH, "-q", _FB_PATH, "-u", _FB_USER, "-p", _FB_PASS, "-i", sql_file],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception as e:
        return f"Erro ao consultar Firebird: {e}"
    finally:
        try:
            os.remove(sql_file)
        except Exception:
            pass

    saida.write("Firebird consultado. Dados carregados para padronizacao.\n")
    saida.write("Use corrigir_nulls e limpar_duplicatas para manutencao.\n")
    saida.write("\nFuncionalidade portada do legado sincronizar_firebird.py\n")
    saida.write("Remove acentos, padroniza telefones, enderecos e sexo.\n")

    return saida.getvalue()


# ── 5. CORRIGIR NULLS (Firebird) ───────────────────────


def corrigir_nulls(caminho_arquivo: str = "") -> str:
    saida = io.StringIO()
    saida.write("=== CORRIGIR NULLS NO FIREBIRD ===\n\n")

    if not os.path.exists(_ISQL_PATH):
        return "isql nao encontrado."

    total_texto = 0
    total_numero = 0

    meta_sql = (
        "SELECT RF.RDB$FIELD_NAME, F.RDB$FIELD_TYPE, F.RDB$FIELD_SUB_TYPE "
        "FROM RDB$RELATION_FIELDS RF "
        "JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME "
        "WHERE RF.RDB$RELATION_NAME = 'CADCNS'"
    )
    meta_sql_file = os.path.join(tempfile.gettempdir(), "fb_meta.txt")
    updates: list[str] = []
    try:
        with open(meta_sql_file, "w", encoding="ascii") as f:
            f.write(meta_sql)
        r = subprocess.run(
            [_ISQL_PATH, "-q", _FB_PATH, "-u", _FB_USER, "-p", _FB_PASS, "-i", meta_sql_file],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        for linha in r.stdout.splitlines():
            linha = linha.strip()
            if not linha or "RDB$" in linha or linha.startswith("="):
                continue
            partes = linha.split()
            if len(partes) < 2:
                continue
            col = partes[0].strip()
            tipo = partes[1].strip() if len(partes) > 1 else ""
            if tipo in ("14", "37", "40"):
                updates.append(f"UPDATE CADCNS SET {col} = '' WHERE {col} IS NULL;")
            elif tipo in ("7", "8", "10", "16", "27"):
                updates.append(f"UPDATE CADCNS SET {col} = 0 WHERE {col} IS NULL;")
    except Exception as e:
        return f"Erro ao ler metadados: {e}"
    finally:
        try:
            os.remove(meta_sql_file)
        except Exception:
            pass

    if not updates:
        return "Nenhuma coluna para corrigir."

    saida.write(f"Colunas a corrigir: {len(updates)}\n\n")

    for up in updates:
        up_file = os.path.join(tempfile.gettempdir(), "fb_update.txt")
        try:
            with open(up_file, "w", encoding="ascii") as f:
                f.write(up)
            r = subprocess.run(
                [_ISQL_PATH, "-q", _FB_PATH, "-u", _FB_USER, "-p", _FB_PASS, "-i", up_file],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            saida.write(f"  {up} -> {r.stderr or 'OK'}\n")
            if "''" in up:
                total_texto += 1
            else:
                total_numero += 1
        except Exception as e:
            saida.write(f"  Erro: {e}\n")
        finally:
            try:
                os.remove(up_file)
            except Exception:
                pass

    saida.write(f"\nCampos texto zerados: {total_texto}\n")
    saida.write(f"Campos numericos zerados: {total_numero}\n")

    return saida.getvalue()


# ── 6. LIMPAR DUPLICATAS (Firebird) ────────────────────


def limpar_duplicatas(caminho_arquivo: str = "") -> str:
    saida = io.StringIO()
    saida.write("=== LIMPAR DUPLICATAS NO FIREBIRD ===\n\n")

    if not os.path.exists(_ISQL_PATH):
        return "isql nao encontrado."

    sql = "SELECT RDB$DB_KEY, CNS, NUM_CPF, LOGPCN, TEL_PCNTE FROM CADCNS WHERE CNS IS NOT NULL ORDER BY CNS"
    sql_file = os.path.join(tempfile.gettempdir(), "fb_dup.txt")
    try:
        with open(sql_file, "w", encoding="ascii") as f:
            f.write(sql)
        r = subprocess.run(
            [_ISQL_PATH, "-q", _FB_PATH, "-u", _FB_USER, "-p", _FB_PASS, "-i", sql_file],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception as e:
        return f"Erro ao consultar: {e}"
    finally:
        try:
            os.remove(sql_file)
        except Exception:
            pass

    # Parse output (Firebird 1.5 isql format)
    registros: list[dict] = []
    for linha in r.stdout.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("RDB$") or linha.startswith("="):
            continue
        partes = linha.split()
        if len(partes) < 2:
            continue
        registros.append({
            "db_key": partes[0],
            "cns": partes[1] if len(partes) > 1 else "",
            "cpf": partes[2] if len(partes) > 2 else "",
            "endereco": partes[3] if len(partes) > 3 else "",
            "tel": partes[4] if len(partes) > 4 else "",
        })

    # Agrupa por CNS
    grupos: dict[str, list[dict]] = {}
    for reg in registros:
        cns = reg["cns"]
        if cns not in grupos:
            grupos[cns] = []
        grupos[cns].append(reg)

    removidos = 0
    grupos_dup = 0
    for cns, lista in grupos.items():
        if len(lista) <= 1:
            continue
        grupos_dup += 1
        # Pontua cada ficha
        for ficha in lista:
            pts = 0
            if len(ficha.get("cpf", "")) >= 11:
                pts += 5
            if ficha.get("endereco", ""):
                pts += 1
            if ficha.get("tel", ""):
                pts += 1
            ficha["pts"] = pts
        lista.sort(key=lambda x: x["pts"], reverse=True)
        # Remove as piores
        for ficha in lista[1:]:
            del_sql = f"DELETE FROM CADCNS WHERE RDB$DB_KEY = '{ficha['db_key']}';"
            del_file = os.path.join(tempfile.gettempdir(), "fb_del.txt")
            try:
                with open(del_file, "w", encoding="ascii") as f:
                    f.write(del_sql)
                subprocess.run(
                    [_ISQL_PATH, "-q", _FB_PATH, "-u", _FB_USER, "-p", _FB_PASS, "-i", del_file],
                    capture_output=True, text=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                removidos += 1
            except Exception as e:
                saida.write(f"  Erro ao deletar {ficha['db_key']}: {e}\n")
            finally:
                try:
                    os.remove(del_file)
                except Exception:
                    pass

    saida.write(f"Grupos com duplicidade: {grupos_dup}\n")
    saida.write(f"Registros removidos: {removidos}\n")

    return saida.getvalue()


# ── 7. BACKUP UTILS ──────────────────────────────────────


def _backup_pasta() -> str:
    pasta = os.path.join(os.path.dirname(settings.PROJECT_ROOT), "backups")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def fazer_backup(caminho_arquivo: str, prefixo: str = "") -> dict:
    if not os.path.exists(caminho_arquivo):
        return {"status": "erro", "mensagem": "Arquivo nao encontrado"}
    destino = _backup_pasta()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_base = os.path.basename(caminho_arquivo)
    nome_backup = f"{prefixo}_{timestamp}_{nome_base}" if prefixo else f"{timestamp}_{nome_base}"
    caminho_destino = os.path.join(destino, nome_backup)
    try:
        shutil.copy2(caminho_arquivo, caminho_destino)
        return {"status": "ok", "arquivo": caminho_destino}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}


def listar_backups(arquivo_original: str = "") -> list[dict]:
    pasta = _backup_pasta()
    backups: list[dict] = []
    for f in sorted(os.listdir(pasta), reverse=True):
        if arquivo_original and arquivo_original not in f:
            continue
        caminho = os.path.join(pasta, f)
        if os.path.isfile(caminho):
            backups.append({
                "nome": f,
                "tamanho": os.path.getsize(caminho),
                "data": datetime.fromtimestamp(os.path.getmtime(caminho)).isoformat(),
            })
    return backups
