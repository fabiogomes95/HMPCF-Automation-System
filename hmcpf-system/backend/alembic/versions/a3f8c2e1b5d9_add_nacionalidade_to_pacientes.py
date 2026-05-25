"""add_nacionalidade_to_pacientes

Revision ID: a3f8c2e1b5d9
Revises: f61017de2d75
Create Date: 2026-05-24 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f8c2e1b5d9'
down_revision: Union[str, Sequence[str], None] = 'f61017de2d75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pacientes', sa.Column('nacionalidade', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('pacientes', 'nacionalidade')
