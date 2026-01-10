"""add_keyword_ranking_tracking

Revision ID: 6c8a12d3e4f5
Revises: 5afe231c7b22
Create Date: 2026-01-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6c8a12d3e4f5'
down_revision: Union[str, None] = '5afe231c7b22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tracking fields to keywords table
    op.add_column('keywords', sa.Column('is_tracked', sa.Boolean(), nullable=True, default=False))
    op.add_column('keywords', sa.Column('current_position', sa.Integer(), nullable=True))
    op.add_column('keywords', sa.Column('previous_position', sa.Integer(), nullable=True))
    op.add_column('keywords', sa.Column('best_position', sa.Integer(), nullable=True))
    op.add_column('keywords', sa.Column('ranking_url', sa.Text(), nullable=True))
    op.add_column('keywords', sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True))

    # Create index on is_tracked for efficient querying
    op.create_index('ix_keywords_is_tracked', 'keywords', ['is_tracked'], unique=False)

    # Set default value for existing rows
    op.execute("UPDATE keywords SET is_tracked = false WHERE is_tracked IS NULL")

    # Make is_tracked not nullable after setting defaults
    op.alter_column('keywords', 'is_tracked', nullable=False, server_default='false')

    # Create keyword_rankings table for historical data
    op.create_table(
        'keyword_rankings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('keyword_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('serp_features', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=dict),
        sa.Column('competitor_positions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=list),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['keyword_id'], ['keywords.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for keyword_rankings
    op.create_index('ix_keyword_rankings_id', 'keyword_rankings', ['id'], unique=False)
    op.create_index('ix_keyword_rankings_keyword_id', 'keyword_rankings', ['keyword_id'], unique=False)
    op.create_index('ix_keyword_rankings_site_id', 'keyword_rankings', ['site_id'], unique=False)
    op.create_index('ix_keyword_rankings_checked_at', 'keyword_rankings', ['checked_at'], unique=False)


def downgrade() -> None:
    # Drop keyword_rankings table and indexes
    op.drop_index('ix_keyword_rankings_checked_at', table_name='keyword_rankings')
    op.drop_index('ix_keyword_rankings_site_id', table_name='keyword_rankings')
    op.drop_index('ix_keyword_rankings_keyword_id', table_name='keyword_rankings')
    op.drop_index('ix_keyword_rankings_id', table_name='keyword_rankings')
    op.drop_table('keyword_rankings')

    # Remove tracking fields from keywords table
    op.drop_index('ix_keywords_is_tracked', table_name='keywords')
    op.drop_column('keywords', 'last_checked_at')
    op.drop_column('keywords', 'ranking_url')
    op.drop_column('keywords', 'best_position')
    op.drop_column('keywords', 'previous_position')
    op.drop_column('keywords', 'current_position')
    op.drop_column('keywords', 'is_tracked')
