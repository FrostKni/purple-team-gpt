"""Initial schema for Purple Team GPT.

Creates the sessions, findings, and events tables for
PostgreSQL persistence.

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

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
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('target', sa.String(500), nullable=False),
        sa.Column('scope', sa.Text(), nullable=True, server_default=''),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('initialization_error', sa.Text(), nullable=True),
    )
    
    # Create indexes for sessions
    op.create_index('ix_sessions_status', 'sessions', ['status'])
    op.create_index('ix_sessions_status_created', 'sessions', ['status', 'created_at'])
    op.create_index('ix_sessions_last_activity', 'sessions', ['last_activity_at'])
    
    # Create findings table
    op.create_table(
        'findings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent', sa.String(10), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('tool', sa.String(100), nullable=True, server_default=''),
        sa.Column('cve', sa.String(50), nullable=True),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for findings
    op.create_index('ix_findings_session_id', 'findings', ['session_id'])
    op.create_index('ix_findings_session_agent', 'findings', ['session_id', 'agent'])
    op.create_index('ix_findings_severity', 'findings', ['severity'])
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent', sa.String(20), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for events
    op.create_index('ix_events_session_id', 'events', ['session_id'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_timestamp', 'events', ['timestamp'])
    op.create_index('ix_events_session_timestamp', 'events', ['session_id', 'timestamp'])


def downgrade() -> None:
    # Drop events table
    op.drop_index('ix_events_session_timestamp', table_name='events')
    op.drop_index('ix_events_timestamp', table_name='events')
    op.drop_index('ix_events_event_type', table_name='events')
    op.drop_index('ix_events_session_id', table_name='events')
    op.drop_table('events')
    
    # Drop findings table
    op.drop_index('ix_findings_severity', table_name='findings')
    op.drop_index('ix_findings_session_agent', table_name='findings')
    op.drop_index('ix_findings_session_id', table_name='findings')
    op.drop_table('findings')
    
    # Drop sessions table
    op.drop_index('ix_sessions_last_activity', table_name='sessions')
    op.drop_index('ix_sessions_status_created', table_name='sessions')
    op.drop_index('ix_sessions_status', table_name='sessions')
    op.drop_table('sessions')