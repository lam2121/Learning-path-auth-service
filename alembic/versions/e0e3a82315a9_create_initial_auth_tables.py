"""create_initial_auth_tables

Revision ID: e0e3a82315a9
Revises: 
Create Date: 2026-08-21 09:18:01.750638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e0e3a82315a9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. users table ────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', mysql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('role', sa.String(length=50), server_default=sa.text("'employee'"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='Master identity table for all applications'
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # ── 2. refresh_tokens table ───────────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', mysql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('user_id', mysql.BIGINT(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('device_info', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    # ── 3. otp_rate_limit table ───────────────────────────────────────────────
    op.create_table(
        'otp_rate_limit',
        sa.Column('id', mysql.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('request_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('verify_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('window_start', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_otp_rate_limit_email'), 'otp_rate_limit', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_otp_rate_limit_email'), table_name='otp_rate_limit')
    op.drop_table('otp_rate_limit')

    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
