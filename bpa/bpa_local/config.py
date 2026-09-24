"""Configuração do BPA local.

Carrega os .env ANTES de qualquer módulo de domínio ser importado — o
bpa_gerador lê FIREBIRD_* e BPA_LOTES_DIR do ambiente na importação.
Prioridade (o primeiro valor encontrado vale):
  1. bpa/.env        — este notebook (Firebird, bpa_leitura, pastas)
  2. backend/.env    — fallback do servidor (desenvolvimento)
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent  # bpa/
RAIZ = BASE.parent

load_dotenv(BASE / ".env")
load_dotenv(RAIZ / "backend" / ".env", override=False)

# Pasta dos lotes: nos 2 notebooks é C:\BPA\bpa_lotes (ao lado do BPA Magnético).
# Sem BPA_LOTES_DIR em nenhum .env, usa ela se o C:\BPA existir -- nunca a pasta do
# sistema por engano.
if not os.getenv("BPA_LOTES_DIR"):
    _padrao = Path(r"C:\BPA\bpa_lotes")
    os.environ["BPA_LOTES_DIR"] = str(_padrao if _padrao.parent.is_dir() else BASE / "bpa_lotes")

PORTA = int(os.getenv("BPA_DIGITACAO_PORT", "8503"))

# Quem pode chamar este BPA pelo navegador: o sistema do hospital e a própria
# página local. Qualquer outro site aberto no notebook é recusado — sem isso,
# uma página qualquer poderia mandar gravar/gerar no Firebird deste PC.
ORIGENS_SISTEMA = {
    o.strip().rstrip("/")
    for o in os.getenv(
        "BPA_ORIGENS_PERMITIDAS", "http://192.168.1.29:8001,http://desktop-9c4s1co:8001"
    ).split(",")
    if o.strip()
}
ORIGENS_LOCAIS = {f"http://localhost:{PORTA}", f"http://127.0.0.1:{PORTA}"}

POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "hmpcf"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

# Bootstrap offline da página atual (reaproveitado do sistema antigo)
