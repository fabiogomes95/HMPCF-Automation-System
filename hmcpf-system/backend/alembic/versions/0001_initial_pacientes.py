"""initial_pacientes

Revision ID: 0001
Revises:
Create Date: 2026-05-23

BANCO JÁ POPULADO?
    Se a tabela pacientes já existir (migração SQLite→PG já executada), NÃO
    rode upgrade — apenas marque como aplicada:

        cd backend
        alembic stamp 0001

BANCO NOVO?
    Execute normalmente:

        cd backend
        alembic upgrade head
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pacientes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("CNS", sa.Text(), nullable=True),
        sa.Column("NUM_CPF", sa.String(length=11), nullable=True),
        sa.Column("NOME", sa.Text(), nullable=True),
        sa.Column("DTNASC", sa.String(length=8), nullable=True),
        sa.Column("SEXO", sa.String(length=1), nullable=True),
        sa.Column("RACA", sa.String(length=2), nullable=True),
        sa.Column("MAEPCN", sa.Text(), nullable=True),
        sa.Column("LOGPCN", sa.Text(), nullable=False, server_default="principal"),
        sa.Column("NUMPCN", sa.Text(), nullable=False, server_default="s/n"),
        sa.Column("BAIRRO_PCNTE", sa.Text(), nullable=False, server_default="centro"),
        sa.Column("NMRES", sa.Text(), nullable=True),
        sa.Column("DDTEL_PCNTE", sa.String(length=3), nullable=True),
        sa.Column("TEL_PCNTE", sa.String(length=12), nullable=True),
        sa.Column("nomeSocial", sa.Text(), nullable=True),
        sa.Column("idade", sa.Text(), nullable=True),
        sa.Column("civil", sa.Text(), nullable=True),
        sa.Column("ocupacao", sa.Text(), nullable=True),
        sa.Column("responsavel", sa.Text(), nullable=True),
        sa.Column("cidade", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=2), nullable=True),
        sa.Column(
            "migrated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pac_cpf", "pacientes", ["NUM_CPF"])
    op.create_index("idx_pac_cns", "pacientes", ["CNS"])
    op.create_index("idx_pac_nome", "pacientes", ["NOME"])


def downgrade() -> None:
    op.drop_index("idx_pac_nome", table_name="pacientes")
    op.drop_index("idx_pac_cns", table_name="pacientes")
    op.drop_index("idx_pac_cpf", table_name="pacientes")
    op.drop_table("pacientes")
