"""add_registro_to_recepcao_atendimentos

Revision ID: b1c2d3e4f5a6
Revises: a3f8c2e1b5d9
Create Date: 2026-05-24 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a3f8c2e1b5d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recepcao_atendimentos",
        sa.Column("registro", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recepcao_atendimentos", "registro")
