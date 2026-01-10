"""add_usage_tracking_tables

Revision ID: 8e0c34f5g6h8
Revises: 7d9b23e4f6a7
Create Date: 2026-01-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8e0c34f5g6h8'
down_revision: Union[str, None] = '7d9b23e4f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenant_usage table for monthly usage tracking
    op.create_table(
        'tenant_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('api_calls', sa.Integer(), default=0),
        sa.Column('pages_crawled', sa.Integer(), default=0),
        sa.Column('keywords_researched', sa.Integer(), default=0),
        sa.Column('audits_run', sa.Integer(), default=0),
        sa.Column('content_generated', sa.Integer(), default=0),
        sa.Column('js_renders', sa.Integer(), default=0),
        sa.Column('endpoint_usage', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'month', name='uq_tenant_usage_month'),
    )
    op.create_index('ix_tenant_usage_tenant_id', 'tenant_usage', ['tenant_id'])
    op.create_index('ix_tenant_usage_month', 'tenant_usage', ['month'])

    # Create tenant_quotas table for custom quota overrides
    op.create_table(
        'tenant_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('monthly_api_calls', sa.Integer(), nullable=True),
        sa.Column('monthly_crawl_pages', sa.Integer(), nullable=True),
        sa.Column('monthly_keyword_lookups', sa.Integer(), nullable=True),
        sa.Column('monthly_audits', sa.Integer(), nullable=True),
        sa.Column('monthly_content_generations', sa.Integer(), nullable=True),
        sa.Column('monthly_js_renders', sa.Integer(), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_tenant_quotas_tenant_id', 'tenant_quotas', ['tenant_id'])

    # Create rate_limit_events table for logging rate limit/quota exceeded events
    op.create_table(
        'rate_limit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('limit_type', sa.String(50), nullable=False),
        sa.Column('limit_value', sa.Integer(), nullable=False),
        sa.Column('current_value', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_rate_limit_events_tenant_id', 'rate_limit_events', ['tenant_id'])
    op.create_index('ix_rate_limit_events_created_at', 'rate_limit_events', ['created_at'])


def downgrade() -> None:
    # Drop rate_limit_events table
    op.drop_index('ix_rate_limit_events_created_at', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_tenant_id', table_name='rate_limit_events')
    op.drop_table('rate_limit_events')

    # Drop tenant_quotas table
    op.drop_index('ix_tenant_quotas_tenant_id', table_name='tenant_quotas')
    op.drop_table('tenant_quotas')

    # Drop tenant_usage table
    op.drop_index('ix_tenant_usage_month', table_name='tenant_usage')
    op.drop_index('ix_tenant_usage_tenant_id', table_name='tenant_usage')
    op.drop_table('tenant_usage')
