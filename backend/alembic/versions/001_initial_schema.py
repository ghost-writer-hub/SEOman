"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE tenant_status AS ENUM ('active', 'suspended', 'trial')")
    op.execute("CREATE TYPE user_role AS ENUM ('super_admin', 'tenant_admin', 'seo_manager', 'read_only')")
    op.execute("CREATE TYPE crawl_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')")
    op.execute("CREATE TYPE audit_status AS ENUM ('pending', 'running', 'completed', 'failed')")
    op.execute("CREATE TYPE issue_severity AS ENUM ('critical', 'high', 'medium', 'low', 'info')")
    op.execute("CREATE TYPE plan_status AS ENUM ('draft', 'active', 'completed', 'archived')")
    op.execute("CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'skipped')")
    op.execute("CREATE TYPE content_status AS ENUM ('pending', 'ready', 'draft', 'review', 'published', 'failed')")
    
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('status', sa.Enum('active', 'suspended', 'trial', name='tenant_status'), 
                  nullable=False, server_default='trial'),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('max_sites', sa.Integer, server_default='10'),
        sa.Column('max_pages_per_crawl', sa.Integer, server_default='20000'),
        sa.Column('max_keywords', sa.Integer, server_default='1000'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now()),
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.Enum('super_admin', 'tenant_admin', 'seo_manager', 'read_only', 
                                   name='user_role'), nullable=False, server_default='read_only'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create sites table
    op.create_table(
        'sites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('audit_schedule', sa.String(50)),
        sa.Column('last_audit_at', sa.DateTime(timezone=True)),
        sa.Column('next_audit_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_sites_tenant_id', 'sites', ['tenant_id'])
    
    # Create crawl_jobs table
    op.create_table(
        'crawl_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', 'paused',
                                     name='crawl_status'), nullable=False, server_default='pending'),
        sa.Column('max_pages', sa.Integer, server_default='1000'),
        sa.Column('pages_crawled', sa.Integer, server_default='0'),
        sa.Column('issues_found', sa.Integer, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_crawl_jobs_site_id', 'crawl_jobs', ['site_id'])
    op.create_index('ix_crawl_jobs_status', 'crawl_jobs', ['status'])
    
    # Create crawl_pages table
    op.create_table(
        'crawl_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('crawl_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('crawl_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('status_code', sa.Integer),
        sa.Column('title', sa.String(512)),
        sa.Column('meta_description', sa.String(1024)),
        sa.Column('h1', sa.String(512)),
        sa.Column('word_count', sa.Integer, server_default='0'),
        sa.Column('load_time_ms', sa.Integer),
        sa.Column('issues', postgresql.JSONB, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_crawl_pages_crawl_id', 'crawl_pages', ['crawl_id'])
    
    # Create audit_runs table
    op.create_table(
        'audit_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed',
                                     name='audit_status'), nullable=False, server_default='pending'),
        sa.Column('audit_type', sa.String(50), server_default='full'),
        sa.Column('score', sa.Integer),
        sa.Column('issues_count', sa.Integer, server_default='0'),
        sa.Column('critical_count', sa.Integer, server_default='0'),
        sa.Column('high_count', sa.Integer, server_default='0'),
        sa.Column('medium_count', sa.Integer, server_default='0'),
        sa.Column('low_count', sa.Integer, server_default='0'),
        sa.Column('ai_recommendations', postgresql.JSONB),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_audit_runs_site_id', 'audit_runs', ['site_id'])
    op.create_index('ix_audit_runs_status', 'audit_runs', ['status'])
    
    # Create seo_issues table
    op.create_table(
        'seo_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('audit_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('audit_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('severity', sa.Enum('critical', 'high', 'medium', 'low', 'info',
                                       name='issue_severity'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('affected_url', sa.String(2048)),
        sa.Column('recommendation', sa.Text),
        sa.Column('is_fixed', sa.Boolean, server_default='false'),
        sa.Column('fixed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_seo_issues_audit_id', 'seo_issues', ['audit_id'])
    op.create_index('ix_seo_issues_severity', 'seo_issues', ['severity'])
    
    # Create keyword_clusters table
    op.create_table(
        'keyword_clusters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('intent', sa.String(100)),
        sa.Column('recommended_content_type', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_keyword_clusters_site_id', 'keyword_clusters', ['site_id'])
    
    # Create keywords table
    op.create_table(
        'keywords',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cluster_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('keyword_clusters.id', ondelete='SET NULL'), nullable=True),
        sa.Column('keyword', sa.String(500), nullable=False),
        sa.Column('search_volume', sa.Integer),
        sa.Column('cpc', sa.Float),
        sa.Column('competition', sa.Float),
        sa.Column('difficulty', sa.Integer),
        sa.Column('intent', sa.String(50)),
        sa.Column('current_position', sa.Integer),
        sa.Column('previous_position', sa.Integer),
        sa.Column('is_tracked', sa.Boolean, server_default='false'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_keywords_site_id', 'keywords', ['site_id'])
    op.create_index('ix_keywords_keyword', 'keywords', ['keyword'])
    op.create_index('ix_keywords_cluster_id', 'keywords', ['cluster_id'])
    
    # Create seo_plans table
    op.create_table(
        'seo_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.Enum('draft', 'active', 'completed', 'archived',
                                     name='plan_status'), nullable=False, server_default='draft'),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('goals', postgresql.JSONB, server_default='[]'),
        sa.Column('progress_percent', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_seo_plans_site_id', 'seo_plans', ['site_id'])
    op.create_index('ix_seo_plans_status', 'seo_plans', ['status'])
    
    # Create seo_tasks table
    op.create_table(
        'seo_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('seo_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'skipped',
                                     name='task_status'), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer, server_default='1'),
        sa.Column('category', sa.String(100)),
        sa.Column('estimated_hours', sa.Float),
        sa.Column('due_date', sa.Date),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_seo_tasks_plan_id', 'seo_tasks', ['plan_id'])
    op.create_index('ix_seo_tasks_status', 'seo_tasks', ['status'])
    
    # Create content_briefs table
    op.create_table(
        'content_briefs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_keyword', sa.String(500), nullable=False),
        sa.Column('title_suggestions', postgresql.JSONB, server_default='[]'),
        sa.Column('meta_description', sa.String(500)),
        sa.Column('target_word_count', sa.Integer, server_default='1500'),
        sa.Column('content_outline', postgresql.JSONB, server_default='[]'),
        sa.Column('keywords_to_include', postgresql.JSONB, server_default='[]'),
        sa.Column('internal_links', postgresql.JSONB, server_default='[]'),
        sa.Column('status', sa.Enum('pending', 'ready', 'draft', 'review', 'published', 'failed',
                                     name='content_status'), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_content_briefs_site_id', 'content_briefs', ['site_id'])
    op.create_index('ix_content_briefs_status', 'content_briefs', ['status'])
    
    # Create content_drafts table
    op.create_table(
        'content_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('brief_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('content_briefs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text),
        sa.Column('word_count', sa.Integer, server_default='0'),
        sa.Column('version', sa.Integer, server_default='1'),
        sa.Column('status', sa.Enum('pending', 'ready', 'draft', 'review', 'published', 'failed',
                                     name='content_status', create_type=False), 
                  nullable=False, server_default='draft'),
        sa.Column('seo_score', sa.Integer),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index('ix_content_drafts_brief_id', 'content_drafts', ['brief_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('content_drafts')
    op.drop_table('content_briefs')
    op.drop_table('seo_tasks')
    op.drop_table('seo_plans')
    op.drop_table('keywords')
    op.drop_table('keyword_clusters')
    op.drop_table('seo_issues')
    op.drop_table('audit_runs')
    op.drop_table('crawl_pages')
    op.drop_table('crawl_jobs')
    op.drop_table('sites')
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS content_status')
    op.execute('DROP TYPE IF EXISTS task_status')
    op.execute('DROP TYPE IF EXISTS plan_status')
    op.execute('DROP TYPE IF EXISTS issue_severity')
    op.execute('DROP TYPE IF EXISTS audit_status')
    op.execute('DROP TYPE IF EXISTS crawl_status')
    op.execute('DROP TYPE IF EXISTS user_role')
    op.execute('DROP TYPE IF EXISTS tenant_status')
