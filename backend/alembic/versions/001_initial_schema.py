"""Initial schema with users, incidents, analyses, status history, correlations, and audit logs

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-16 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='VIEWER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Incidents Table
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('service_name', sa.String(length=128), nullable=False),
        sa.Column('environment', sa.String(length=64), nullable=False, server_default='production'),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default='LOW'),
        sa.Column('ai_severity', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='OPEN'),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('affected_endpoint', sa.String(length=255), nullable=True),
        sa.Column('request_metadata', sa.JSON(), nullable=True),
        sa.Column('error_frequency', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('affected_users', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deployment_version', sa.String(length=64), nullable=True),
        sa.Column('additional_context', sa.JSON(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_incidents_id'), 'incidents', ['id'], unique=False)
    op.create_index(op.f('ix_incidents_title'), 'incidents', ['title'], unique=False)
    op.create_index(op.f('ix_incidents_service_name'), 'incidents', ['service_name'], unique=False)
    op.create_index(op.f('ix_incidents_environment'), 'incidents', ['environment'], unique=False)
    op.create_index(op.f('ix_incidents_severity'), 'incidents', ['severity'], unique=False)
    op.create_index(op.f('ix_incidents_status'), 'incidents', ['status'], unique=False)
    op.create_index(op.f('ix_incidents_created_at'), 'incidents', ['created_at'], unique=False)

    # 3. Incident Analyses Table
    op.create_table(
        'incident_analyses',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_provider', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('prompt_version', sa.String(length=64), nullable=False),
        sa.Column('classification', sa.String(length=128), nullable=False),
        sa.Column('ai_severity', sa.String(length=32), nullable=False),
        sa.Column('probable_root_cause', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('impact_assessment', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('immediate_mitigation_steps', sa.JSON(), nullable=False),
        sa.Column('recommended_remediation_steps', sa.JSON(), nullable=False),
        sa.Column('prevention_recommendations', sa.JSON(), nullable=False),
        sa.Column('human_readable_summary', sa.Text(), nullable=False),
        sa.Column('raw_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_incident_analyses_id'), 'incident_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_incident_analyses_incident_id'), 'incident_analyses', ['incident_id'], unique=False)

    # 4. Incident Status History Table
    op.create_table(
        'incident_status_history',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_status', sa.String(length=32), nullable=False),
        sa.Column('new_status', sa.String(length=32), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_incident_status_history_id'), 'incident_status_history', ['id'], unique=False)
    op.create_index(op.f('ix_incident_status_history_incident_id'), 'incident_status_history', ['incident_id'], unique=False)

    # 5. Incident Correlations Table
    op.create_table(
        'incident_correlations',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('related_incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('correlation_score', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_incident_correlations_id'), 'incident_correlations', ['id'], unique=False)
    op.create_index(op.f('ix_incident_correlations_incident_id'), 'incident_correlations', ['incident_id'], unique=False)

    # 6. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_username', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('incident_correlations')
    op.drop_table('incident_status_history')
    op.drop_table('incident_analyses')
    op.drop_table('incidents')
    op.drop_table('users')
