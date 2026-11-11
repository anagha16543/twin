"""create_phase4_nba_and_evidence_tables

Revision ID: e3b8a1c9f4d2
Revises: d72af8b7c997
Create Date: 2026-10-28 00:01:00.000000+00:00

Phase 4 Migration:
  - nba_criteria
  - nba_requirements
  - requirement_evaluations
  - documents
  - requirement_evidence
  - document_chunks (with pgvector support on PostgreSQL)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b8a1c9f4d2'
down_revision: Union[str, None] = 'd72af8b7c997'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Enable pgvector extension conditionally on PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. nba_criteria
    op.create_table(
        'nba_criteria',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('max_marks', sa.Float(), nullable=False),
        sa.Column('guideline_version', sa.String(length=50), nullable=False, server_default='NBA-UG-TIER-1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_nba_criteria_code', 'nba_criteria', ['code'], unique=True)

    # 2. nba_requirements
    op.create_table(
        'nba_requirements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('criterion_id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=60), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weightage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('evaluation_rule_key', sa.String(length=120), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['criterion_id'], ['nba_criteria.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_nba_requirements_criterion_id', 'nba_requirements', ['criterion_id'])
    op.create_index('ix_nba_requirements_code', 'nba_requirements', ['code'], unique=True)

    # 3. requirement_evaluations
    op.create_table(
        'requirement_evaluations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('requirement_id', sa.Uuid(), nullable=False),
        sa.Column('academic_year_id', sa.Uuid(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('score_attained', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('max_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('mode', sa.String(length=30), nullable=False, server_default='DETERMINISTIC'),
        sa.Column('deterministic_metrics', sa.JSON(), nullable=True),
        sa.Column('limitations', sa.JSON(), nullable=True),
        sa.Column('ai_interpretation', sa.Text(), nullable=True),
        sa.Column('ai_findings', sa.JSON(), nullable=True),
        sa.Column('ai_request_id', sa.String(length=64), nullable=True),
        sa.Column('ai_correlation_id', sa.String(length=64), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('evaluated_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['requirement_id'], ['nba_requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['evaluated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_requirement_evaluations_requirement_id', 'requirement_evaluations', ['requirement_id'])
    op.create_index('ix_requirement_evaluations_academic_year_id', 'requirement_evaluations', ['academic_year_id'])
    op.create_index('ix_requirement_evaluations_department', 'requirement_evaluations', ['department'])
    op.create_index('ix_requirement_evaluations_evaluated_at', 'requirement_evaluations', ['evaluated_at'])

    # 4. documents
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=512), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('academic_year_id', sa.Uuid(), nullable=False),
        sa.Column('uploaded_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('parent_document_id', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('processing_status', sa.String(length=30), nullable=False, server_default='UPLOADED'),
        sa.Column('validation_status', sa.String(length=30), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('validated_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['deleted_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['validated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stored_filename'),
    )
    op.create_index('ix_documents_sha256_hash', 'documents', ['sha256_hash'])
    op.create_index('ix_documents_department', 'documents', ['department'])
    op.create_index('ix_documents_academic_year_id', 'documents', ['academic_year_id'])
    op.create_index('ix_documents_uploaded_by_user_id', 'documents', ['uploaded_by_user_id'])
    op.create_index('ix_documents_is_current', 'documents', ['is_current'])
    op.create_index('ix_documents_parent_document_id', 'documents', ['parent_document_id'])
    op.create_index('ix_documents_is_deleted', 'documents', ['is_deleted'])
    op.create_index('ix_documents_processing_status', 'documents', ['processing_status'])

    # 5. requirement_evidence
    op.create_table(
        'requirement_evidence',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('requirement_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('relevance_note', sa.String(length=500), nullable=True),
        sa.Column('linked_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['requirement_id'], ['nba_requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['linked_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('requirement_id', 'document_id', name='uq_req_document'),
    )
    op.create_index('ix_requirement_evidence_requirement_id', 'requirement_evidence', ['requirement_id'])
    op.create_index('ix_requirement_evidence_document_id', 'requirement_evidence', ['document_id'])

    # 6. document_chunks
    if is_postgres:
        try:
            from pgvector.sqlalchemy import Vector
            embedding_type = Vector(384)
        except Exception:
            embedding_type = sa.JSON()
    else:
        embedding_type = sa.JSON()

    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('section_heading', sa.String(length=300), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding_model', sa.String(length=120), nullable=True),
        sa.Column('embedding_dimensions', sa.Integer(), nullable=True),
        sa.Column('embedding', embedding_type, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_doc_chunk_index'),
    )
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])
    op.create_index('ix_document_chunks_content_hash', 'document_chunks', ['content_hash'])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('document_chunks')
    op.drop_table('requirement_evidence')
    op.drop_table('documents')
    op.drop_table('requirement_evaluations')
    op.drop_table('nba_requirements')
    op.drop_table('nba_criteria')
