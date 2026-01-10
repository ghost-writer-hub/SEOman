"""add_alerts_and_monitoring

Revision ID: 9f1d45g6h7i9
Revises: 8e0c34f5g6h8
Create Date: 2026-01-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f1d45g6h7i9'
down_revision: Union[str, None] = '8e0c34f5g6h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE alerttype AS ENUM ('uptime', 'ranking_drop', 'audit_score_drop', 'index_status')")
    op.execute("CREATE TYPE alertseverity AS ENUM ('info', 'warning', 'critical')")
    op.execute("CREATE TYPE alertrulestatus AS ENUM ('active', 'paused', 'disabled')")
    op.execute("CREATE TYPE alerteventstatus AS ENUM ('active', 'acknowledged', 'resolved')")

    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('alert_type', postgresql.ENUM('uptime', 'ranking_drop', 'audit_score_drop', 'index_status', name='alerttype', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'paused', 'disabled', name='alertrulestatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('conditions', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=False, server_default='["email"]'),
        sa.Column('notification_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_alert_rules_tenant_id', 'alert_rules', ['tenant_id'])
    op.create_index('ix_alert_rules_site_id', 'alert_rules', ['site_id'])
    op.create_index('ix_alert_rules_alert_type', 'alert_rules', ['alert_type'])
    op.create_index('ix_alert_rules_status', 'alert_rules', ['status'])

    # Create alert_events table
    op.create_table(
        'alert_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alert_type', postgresql.ENUM('uptime', 'ranking_drop', 'audit_score_drop', 'index_status', name='alerttype', create_type=False), nullable=False),
        sa.Column('severity', postgresql.ENUM('info', 'warning', 'critical', name='alertseverity', create_type=False), nullable=False, server_default='info'),
        sa.Column('status', postgresql.ENUM('active', 'acknowledged', 'resolved', name='alerteventstatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('notifications_sent', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_alert_events_tenant_id', 'alert_events', ['tenant_id'])
    op.create_index('ix_alert_events_site_id', 'alert_events', ['site_id'])
    op.create_index('ix_alert_events_rule_id', 'alert_events', ['rule_id'])
    op.create_index('ix_alert_events_alert_type', 'alert_events', ['alert_type'])
    op.create_index('ix_alert_events_status', 'alert_events', ['status'])
    op.create_index('ix_alert_events_created_at', 'alert_events', ['created_at'])

    # Create uptime_checks table
    op.create_table(
        'uptime_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_up', sa.Boolean(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_uptime_checks_tenant_id', 'uptime_checks', ['tenant_id'])
    op.create_index('ix_uptime_checks_site_id', 'uptime_checks', ['site_id'])
    op.create_index('ix_uptime_checks_checked_at', 'uptime_checks', ['checked_at'])
    # Composite index for efficient uptime queries
    op.create_index('ix_uptime_checks_site_checked', 'uptime_checks', ['site_id', 'checked_at'])


def downgrade() -> None:
    # Drop uptime_checks table
    op.drop_index('ix_uptime_checks_site_checked', table_name='uptime_checks')
    op.drop_index('ix_uptime_checks_checked_at', table_name='uptime_checks')
    op.drop_index('ix_uptime_checks_site_id', table_name='uptime_checks')
    op.drop_index('ix_uptime_checks_tenant_id', table_name='uptime_checks')
    op.drop_table('uptime_checks')

    # Drop alert_events table
    op.drop_index('ix_alert_events_created_at', table_name='alert_events')
    op.drop_index('ix_alert_events_status', table_name='alert_events')
    op.drop_index('ix_alert_events_alert_type', table_name='alert_events')
    op.drop_index('ix_alert_events_rule_id', table_name='alert_events')
    op.drop_index('ix_alert_events_site_id', table_name='alert_events')
    op.drop_index('ix_alert_events_tenant_id', table_name='alert_events')
    op.drop_table('alert_events')

    # Drop alert_rules table
    op.drop_index('ix_alert_rules_status', table_name='alert_rules')
    op.drop_index('ix_alert_rules_alert_type', table_name='alert_rules')
    op.drop_index('ix_alert_rules_site_id', table_name='alert_rules')
    op.drop_index('ix_alert_rules_tenant_id', table_name='alert_rules')
    op.drop_table('alert_rules')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS alerteventstatus")
    op.execute("DROP TYPE IF EXISTS alertrulestatus")
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS alerttype")
