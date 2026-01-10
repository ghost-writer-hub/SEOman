"""add_performance_snapshots

Revision ID: a0b1c2d3e4f5
Revises: 9f1d45g6h7i9
Create Date: 2026-01-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = '9f1d45g6h7i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create performance_snapshots table
    op.create_table(
        'performance_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Foreign keys
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audit_run_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Page identification
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('template_type', sa.String(50), nullable=True),
        sa.Column('strategy', sa.String(10), nullable=False),  # mobile, desktop

        # Overall score (0-100)
        sa.Column('performance_score', sa.Integer(), nullable=True),

        # Core Web Vitals - Lab Data (milliseconds except CLS which is ratio)
        sa.Column('lcp_ms', sa.Integer(), nullable=True),       # Largest Contentful Paint
        sa.Column('fid_ms', sa.Integer(), nullable=True),       # First Input Delay
        sa.Column('cls', sa.Float(), nullable=True),            # Cumulative Layout Shift
        sa.Column('fcp_ms', sa.Integer(), nullable=True),       # First Contentful Paint
        sa.Column('ttfb_ms', sa.Integer(), nullable=True),      # Time to First Byte
        sa.Column('tbt_ms', sa.Integer(), nullable=True),       # Total Blocking Time
        sa.Column('speed_index_ms', sa.Integer(), nullable=True),  # Speed Index
        sa.Column('tti_ms', sa.Integer(), nullable=True),       # Time to Interactive
        sa.Column('inp_ms', sa.Integer(), nullable=True),       # Interaction to Next Paint

        # Overall CWV status
        sa.Column('cwv_status', sa.String(20), nullable=True),

        # Raw data storage (JSONB)
        sa.Column('opportunities', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=list),
        sa.Column('diagnostics', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=dict),
        sa.Column('field_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=dict),

        # Timestamp
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audit_run_id'], ['audit_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance_snapshots
    op.create_index('ix_performance_snapshots_id', 'performance_snapshots', ['id'], unique=False)
    op.create_index('ix_performance_snapshots_tenant_id', 'performance_snapshots', ['tenant_id'], unique=False)
    op.create_index('ix_performance_snapshots_site_id', 'performance_snapshots', ['site_id'], unique=False)
    op.create_index('ix_performance_snapshots_audit_run_id', 'performance_snapshots', ['audit_run_id'], unique=False)
    op.create_index('ix_performance_snapshots_url', 'performance_snapshots', ['url'], unique=False)
    op.create_index('ix_performance_snapshots_template_type', 'performance_snapshots', ['template_type'], unique=False)
    op.create_index('ix_performance_snapshots_checked_at', 'performance_snapshots', ['checked_at'], unique=False)

    # Composite index for common queries (site + strategy + checked_at)
    op.create_index(
        'ix_performance_snapshots_site_strategy_checked',
        'performance_snapshots',
        ['site_id', 'strategy', 'checked_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_performance_snapshots_site_strategy_checked', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_checked_at', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_template_type', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_url', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_audit_run_id', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_site_id', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_tenant_id', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_id', table_name='performance_snapshots')

    # Drop table
    op.drop_table('performance_snapshots')
