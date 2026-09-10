"""unique_otp_rate_limit_email

Revision ID: b7c2a41d9e5f
Revises: e0e3a82315a9
Create Date: 2026-09-10 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c2a41d9e5f'
down_revision: Union[str, None] = 'e0e3a82315a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_otp_rate_limit_email', table_name='otp_rate_limit')
    op.create_index(op.f('ix_otp_rate_limit_email'), 'otp_rate_limit', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_otp_rate_limit_email'), table_name='otp_rate_limit')
    op.create_index('ix_otp_rate_limit_email', 'otp_rate_limit', ['email'], unique=False)
