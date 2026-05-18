"""
CONFIG.PY — Configuração centralizada do HMPCF
===============================================
Carrega configurações de:
1. Arquivo .env na raiz (se existir)
2. Variáveis de ambiente do sistema
3. Valores padrão (funcionam sem .env)

Uso:
    from config import FIREBIRD_PATH, GOOGLE_SHEET_ID, ...
"""

import os
import hashlib


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(
            f"CRÍTICO: {key} não configurada. "
            f"Defina no .env ou na variável de ambiente."
        )
    return val


def _carregar_dotenv() -> None:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, val = line.partition('=')
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key:
                        os.environ.setdefault(key, val)

_carregar_dotenv()

getenv = os.getenv

FIREBIRD_HOST = getenv('FIREBIRD_HOST', 'localhost')
FIREBIRD_PATH = getenv('FIREBIRD_PATH', r'C:/BPA/BPAMAG.GDB')
FIREBIRD_USER = getenv('FIREBIRD_USER', 'SYSDBA')
FIREBIRD_PASSWORD = _require_env('FIREBIRD_PASSWORD')

GOOGLE_SHEET_ID = _require_env('GOOGLE_SHEET_ID')
GOOGLE_CREDENTIALS_PATH = getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
GOOGLE_SCOPE_SHEETS = getenv('GOOGLE_SCOPE_SHEETS', 'https://www.googleapis.com/auth/spreadsheets')
GOOGLE_SCOPE_DRIVE = getenv('GOOGLE_SCOPE_DRIVE', 'https://www.googleapis.com/auth/drive')

CEP_RUA = _require_env('CEP_RUA')
CODIGO_UNIDADE = _require_env('CODIGO_UNIDADE')
FOLHA_CODIGO = getenv('FOLHA_CODIGO', '010')
SEQ_PROFISSIONAL = getenv('SEQ_PROFISSIONAL', '03')

DB_SQLITE = getenv('DB_SQLITE', 'hospital.db')


def _read_admin_password_file() -> str | None:
    path = os.path.join(os.path.dirname(__file__), '.admin_pass')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return None
    return None


def get_admin_password() -> str:
    """Return the current admin password hash.

    Priority: `.admin_pass` file > ENV `ADMIN_PASSWORD`.
    """
    v = _read_admin_password_file()
    if v:
        return v
    return _require_env('ADMIN_PASSWORD')


def _hash_password(passwd: str) -> str:
    return hashlib.sha256(passwd.encode()).hexdigest()


def set_admin_password(newpass: str) -> bool:
    """Persist new admin password (SHA256) to `.admin_pass` file. Returns True on success."""
    path = os.path.join(os.path.dirname(__file__), '.admin_pass')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(_hash_password(newpass or ''))
        return True
    except Exception:
        return False
