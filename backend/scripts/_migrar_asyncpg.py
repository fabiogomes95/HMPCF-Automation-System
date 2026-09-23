"""Script temporario de migracao usando asyncpg (evita problema psycopg2 no Windows)."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

HOST = os.environ["POSTGRES_HOST"]
PORT = int(os.environ["POSTGRES_PORT"])
USER = os.environ["POSTGRES_USER"]
PASSWORD = os.environ["POSTGRES_PASSWORD"]
DB = os.environ["POSTGRES_DB"]


async def main():
    conn = await asyncpg.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB, ssl=False)
    try:
        # --- usuarios ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id               SERIAL PRIMARY KEY,
                username         VARCHAR(50)  NOT NULL UNIQUE,
                password_hash    VARCHAR(60)  NOT NULL,
                role             VARCHAR(30)  NOT NULL,
                ativo            BOOLEAN      NOT NULL DEFAULT true,
                tentativas_falhas SMALLINT    NOT NULL DEFAULT 0,
                bloqueado_ate    TIMESTAMPTZ,
                last_login_at    TIMESTAMPTZ,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
        """)
        print("OK: tabela 'usuarios' garantida.")

        # --- sessoes ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessoes (
                id          SERIAL PRIMARY KEY,
                usuario_id  INTEGER     NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                token_hash  VARCHAR(64) NOT NULL UNIQUE,
                criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
                expira_em   TIMESTAMPTZ NOT NULL,
                ip_criacao  VARCHAR(45)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessoes_expira_em ON sessoes(expira_em)
        """)
        print("OK: tabela 'sessoes' garantida.")

        # --- logs_auditoria ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                id               SERIAL PRIMARY KEY,
                usuario_id       INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                usuario_username VARCHAR(50)  NOT NULL,
                acao             VARCHAR(20)  NOT NULL,
                recurso          VARCHAR(30)  NOT NULL,
                recurso_id       INTEGER      NOT NULL,
                campos_alterados JSON,
                criado_em        TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_auditoria_recurso
            ON logs_auditoria(recurso, recurso_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_auditoria_criado_em
            ON logs_auditoria(criado_em)
        """)
        print("OK: tabela 'logs_auditoria' garantida.")

        # --- coluna sem_documento em pacientes ---
        await conn.execute("""
            ALTER TABLE pacientes
            ADD COLUMN IF NOT EXISTS sem_documento BOOLEAN NOT NULL DEFAULT false
        """)
        print("OK: coluna 'sem_documento' em 'pacientes' garantida.")

        print("\nTodas as migracoes concluidas com sucesso!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
