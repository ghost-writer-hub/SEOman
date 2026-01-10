"""add_js_rendering_fields

Revision ID: 7d9b23e4f6a7
Revises: 6c8a12d3e4f5
Create Date: 2026-01-10 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7d9b23e4f6a7'
down_revision: Union[str, None] = '6c8a12d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add JS rendering fields to crawl_pages table
    op.add_column('crawl_pages', sa.Column('js_rendered', sa.Boolean(), nullable=True, default=False))
    op.add_column('crawl_pages', sa.Column('js_render_time_ms', sa.Integer(), nullable=True))
    op.add_column('crawl_pages', sa.Column('spa_detected', sa.Boolean(), nullable=True, default=False))
    op.add_column('crawl_pages', sa.Column('framework_detected', sa.String(50), nullable=True))

    # Set defaults for existing rows
    op.execute("UPDATE crawl_pages SET js_rendered = false WHERE js_rendered IS NULL")
    op.execute("UPDATE crawl_pages SET spa_detected = false WHERE spa_detected IS NULL")


def downgrade() -> None:
    # Remove JS rendering fields from crawl_pages table
    op.drop_column('crawl_pages', 'framework_detected')
    op.drop_column('crawl_pages', 'spa_detected')
    op.drop_column('crawl_pages', 'js_render_time_ms')
    op.drop_column('crawl_pages', 'js_rendered')
