"""
Conexão PostgreSQL para o novo backend HMPCF.
Lê as credenciais do .env na raiz de hmcpf-system/.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool as pg_pool

try:
    from dotenv import load_dotenv
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env)
except ImportError:
    pass

POSTGRES_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB",       "hmpcf")
POSTGRES_USER     = os.getenv("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "hmpcf2024")

_pool: pg_pool.SimpleConnectionPool | None = None


def get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = pg_pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=10,
        )
    return _pool


def get_pg_conn():
    """Retorna conexão do pool com RealDictCursor como padrão."""
    conn = get_pool().getconn()
    conn.autocommit = False
    return conn


def release_pg_conn(conn) -> None:
    get_pool().putconn(conn)


def close_pool() -> None:
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        _pool = None
