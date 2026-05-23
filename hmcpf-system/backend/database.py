import sqlite3
import os

# hospital.db fica na raiz do projeto (dois níveis acima deste arquivo)
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "hospital.db",
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            CNS TEXT, NUM_CPF TEXT, NOME TEXT, DTNASC TEXT,
            SEXO TEXT, RACA TEXT, MAEPCN TEXT, LOGPCN TEXT,
            NUMPCN TEXT, BAIRRO_PCNTE TEXT, CEPPCN TEXT,
            IBGE TEXT, ETNIA TEXT, NACIONALIDADE TEXT,
            NOME_SOCIAL TEXT, IDADE TEXT, ESTADO_CIVIL TEXT,
            OCUPACAO TEXT, RESPONSAVEL TEXT, TELEFONE TEXT,
            CIDADE TEXT, ESTADO TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT, sus TEXT,
            data_atendimento TEXT, hora_atendimento TEXT,
            registro TEXT, procedencia TEXT,
            enviado_nuvem INTEGER DEFAULT 0,
            paciente_id INTEGER
        )
    """)
    try:
        cur.execute("ALTER TABLE atendimentos ADD COLUMN paciente_id INTEGER")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS terminal_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            terminal_nome TEXT UNIQUE,
            ip_address TEXT,
            ultimo_ping TEXT
        )
    """)

    conn.commit()
    conn.close()
