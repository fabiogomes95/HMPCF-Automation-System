"""remove índices repetidos de CPF e CNS em pacientes

idx_pac_cpf e idx_pac_cns indexavam as mesmas colunas que os índices dos
UNIQUE (pacientes_num_cpf_key, pacientes_cns_key) -- cada cadastro gravava
duas vezes a mesma coisa. As buscas por CPF/CNS passam a usar os do UNIQUE.
Não mexe em nenhum dado.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11
"""
from alembic import op


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('idx_pac_cpf', table_name='pacientes')
    op.drop_index('idx_pac_cns', table_name='pacientes')


def downgrade() -> None:
    op.create_index('idx_pac_cns', 'pacientes', ['cns'], unique=False)
    op.create_index('idx_pac_cpf', 'pacientes', ['num_cpf'], unique=False)
