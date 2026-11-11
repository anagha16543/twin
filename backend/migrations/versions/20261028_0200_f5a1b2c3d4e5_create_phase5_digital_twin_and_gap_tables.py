"""create_phase5_digital_twin_and_gap_tables

Revision ID: f5a1b2c3d4e5
Revises: e3b8a1c9f4d2
Create Date: 2026-10-28 02:00:00.000000+00:00

Phase 5 Migration:
  - nba_gaps
  - nba_corrective_actions
  - notifications
  - system_backup_records
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a1b2c3d4e5'
down_revision: Union[str, None] = 'e3b8a1c9f4d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. nba_gaps
    op.create_table(
        'nba_gaps',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('requirement_id', sa.Uuid(), nullable=False),
        sa.Column('criterion_id', sa.Uuid(), nullable=False),
        sa.Column('academic_year_id', sa.Uuid(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IDENTIFIED'),
        sa.Column('identified_from_evaluation_id', sa.Uuid(), nullable=True),
        sa.Column('responsible_evidence_or_data', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('recommended_action', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['criterion_id'], ['nba_criteria.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['identified_from_evaluation_id'], ['requirement_evaluations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requirement_id'], ['nba_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_nba_gaps_academic_year_id', 'nba_gaps', ['academic_year_id'])
    op.create_index('ix_nba_gaps_criterion_id', 'nba_gaps', ['criterion_id'])
    op.create_index('ix_nba_gaps_department', 'nba_gaps', ['department'])
    op.create_index('ix_nba_gaps_requirement_id', 'nba_gaps', ['requirement_id'])
    op.create_index('ix_nba_gaps_severity', 'nba_gaps', ['severity'])
    op.create_index('ix_nba_gaps_status', 'nba_gaps', ['status'])

    # 2. nba_corrective_actions
    op.create_table(
        'nba_corrective_actions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('gap_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('assigned_to_user_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IDENTIFIED'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['gap_id'], ['nba_gaps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_nba_corrective_actions_assigned_to_user_id', 'nba_corrective_actions', ['assigned_to_user_id'])
    op.create_index('ix_nba_corrective_actions_gap_id', 'nba_corrective_actions', ['gap_id'])
    op.create_index('ix_nba_corrective_actions_status', 'nba_corrective_actions', ['status'])

    # 3. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=100), nullable=False, server_default='SYSTEM'),
        sa.Column('link_url', sa.String(length=500), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_notification_type', 'notifications', ['notification_type'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])

    # 4. system_backup_records
    op.create_table(
        'system_backup_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('backup_identifier', sa.String(length=100), nullable=False),
        sa.Column('backup_type', sa.String(length=50), nullable=False, server_default='FULL'),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='COMPLETED'),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_system_backup_records_backup_identifier', 'system_backup_records', ['backup_identifier'], unique=True)


def downgrade() -> None:
    op.drop_table('system_backup_records')
    op.drop_table('notifications')
    op.drop_table('nba_corrective_actions')
    op.drop_table('nba_gaps')
