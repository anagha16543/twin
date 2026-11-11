"""create criterion 3 attainment and rubric tables

Revision ID: c3a77a1n0001
Revises: a1b2c3d4e5f6
Create Date: 2026-11-12 01:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3a77a1n0001"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "c3_assessment_co_maps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assessment_scheme_id", sa.Uuid(), sa.ForeignKey("assessment_schemes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_outcome_id", sa.Uuid(), sa.ForeignKey("course_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("assessment_scheme_id", name="uq_c3_assessment_one_co"),
    )
    op.create_index("ix_c3_assessment_co_maps_scheme", "c3_assessment_co_maps", ["assessment_scheme_id"])
    op.create_index("ix_c3_assessment_co_maps_co", "c3_assessment_co_maps", ["course_outcome_id"])

    op.create_table(
        "c3_attainment_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("department", sa.String(100), nullable=False, index=True),
        sa.Column("academic_year_id", sa.Uuid(), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_threshold_pct", sa.Float(), nullable=False, server_default="60"),
        sa.Column("level3_pct", sa.Float(), nullable=False, server_default="70"),
        sa.Column("level2_pct", sa.Float(), nullable=False, server_default="60"),
        sa.Column("level1_pct", sa.Float(), nullable=False, server_default="50"),
        sa.Column("cie_weight", sa.Float(), nullable=False, server_default="40"),
        sa.Column("see_weight", sa.Float(), nullable=False, server_default="60"),
        sa.Column("direct_weight", sa.Float(), nullable=False, server_default="80"),
        sa.Column("indirect_weight", sa.Float(), nullable=False, server_default="20"),
        sa.Column("co_target_level", sa.Float(), nullable=False, server_default="2"),
        sa.Column("po_target_level", sa.Float(), nullable=False, server_default="2"),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("department", "academic_year_id", name="uq_c3_config_dept_year"),
    )

    op.create_table(
        "c3_co_indirect",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_outcome_id", sa.Uuid(), sa.ForeignKey("course_outcomes.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("survey_pct", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "c3_po_indirect",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("department", sa.String(100), nullable=False, index=True),
        sa.Column("academic_year_id", sa.Uuid(), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("survey_name", sa.String(120), nullable=False),
        sa.Column("outcome_code", sa.String(20), nullable=False),
        sa.Column("level", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("department", "academic_year_id", "survey_name", "outcome_code", name="uq_c3_po_indirect"),
    )

    op.create_table(
        "c3_attainment_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("department", sa.String(100), nullable=False, index=True),
        sa.Column("academic_year_id", sa.Uuid(), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("computed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("computed_at", sa.DateTime(timezone=True), index=True),
    )

    op.create_table(
        "c3_rubric_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("department", sa.String(100), nullable=False, index=True),
        sa.Column("academic_year_id", sa.Uuid(), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rubric_code", sa.String(10), nullable=False),
        sa.Column("component_key", sa.String(5), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("department", "academic_year_id", "rubric_code", "component_key", name="uq_c3_rubric_score"),
    )


def downgrade() -> None:
    for t in ("c3_rubric_scores", "c3_attainment_snapshots", "c3_po_indirect", "c3_co_indirect",
              "c3_attainment_configs", "c3_assessment_co_maps"):
        op.drop_table(t)
