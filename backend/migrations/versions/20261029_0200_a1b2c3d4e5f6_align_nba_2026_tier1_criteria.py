"""align_nba_2026_tier1_criteria

Revision ID: a1b2c3d4e5f6
Revises: f5a1b2c3d4e5
Create Date: 2026-10-29 02:00:00.000000+00:00

Phase 6 Alignment:
  - Correct Criterion 4 weightages:
      4.2 Success Rate -> 15.0 marks
      4.6 Placement & Higher Studies -> 30.0 marks
      4.7 Professional Activities -> 25.0 marks
  - Correct Criterion 5 weightages:
      5.2 Faculty Qualification Index -> 25.0 marks
      5.5 Faculty Retention -> 10.0 marks
  - Correct Criterion 3 structure & weightages:
      3.2 SEE Question Paper -> 10.0 marks
      3.3 Laboratory Work and Workshop -> 10.0 marks
      3.4 Industrial Training/Internship -> 10.0 marks
      3.5 Projects Evaluation -> 20.0 marks
      3.6 Sustainable Development Goals (SDG) -> 10.0 marks
      3.7 Course Outcome Attainment -> 25.0 marks
      3.8 Program Outcome and PSO Attainment -> 25.0 marks
      REQ_3_COPO -> CO-PO Mapping Completeness (Legacy) -> 0.0 marks
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f5a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. Update Criterion 4 requirements ---
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 15.0 WHERE code = 'REQ_4_2'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 30.0 WHERE code = 'REQ_4_6'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 25.0 WHERE code = 'REQ_4_7'"
        )
    )

    # --- 2. Update Criterion 5 requirements ---
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 25.0 WHERE code = 'REQ_5_2'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 10.0 WHERE code = 'REQ_5_5'"
        )
    )

    # --- 3. Update Criterion 3 requirements ---
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET "
            "title = 'SEE Question Paper Evaluation (3.2)', "
            "evaluation_rule_key = 'criterion3.see_question_paper', "
            "weightage = 10.0, "
            "display_order = 2 "
            "WHERE code = 'REQ_3_2'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET "
            "title = 'Laboratory Work and Workshop (3.3)', "
            "evaluation_rule_key = 'criterion3.lab_workshop', "
            "weightage = 10.0, "
            "display_order = 3 "
            "WHERE code = 'REQ_3_3'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET "
            "title = 'Industrial Training/Internship (3.4)', "
            "evaluation_rule_key = 'criterion3.industrial_training', "
            "weightage = 10.0, "
            "display_order = 4 "
            "WHERE code = 'REQ_3_4'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET "
            "title = 'Projects Evaluation (3.5)', "
            "evaluation_rule_key = 'criterion3.project_evaluation', "
            "weightage = 20.0, "
            "display_order = 5 "
            "WHERE code = 'REQ_3_5'"
        )
    )

    # Check if REQ_3_6 exists; if not, query criterion 3 id and insert
    c3_row = conn.execute(
        sa.text("SELECT id FROM nba_criteria WHERE code = 'CRITERION_3'")
    ).fetchone()

    if c3_row:
        c3_id = c3_row[0]
        req36_exists = conn.execute(
            sa.text("SELECT 1 FROM nba_requirements WHERE code = 'REQ_3_6'")
        ).fetchone()

        now = datetime.now(timezone.utc)
        if not req36_exists:
            new_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    "INSERT INTO nba_requirements (id, criterion_id, code, title, description, weightage, is_mandatory, evaluation_rule_key, display_order, created_at, updated_at) "
                    "VALUES (:id, :criterion_id, 'REQ_3_6', 'Sustainable Development Goals (SDG) (3.6)', 'Evidence of addressing Sustainable Development Goals in curriculum and projects.', 10.0, 1, 'criterion3.sdg_evidence', 6, :created_at, :updated_at)"
                ),
                {"id": new_id, "criterion_id": c3_id, "created_at": now, "updated_at": now},
            )
        else:
            conn.execute(
                sa.text(
                    "UPDATE nba_requirements SET "
                    "title = 'Sustainable Development Goals (SDG) (3.6)', "
                    "evaluation_rule_key = 'criterion3.sdg_evidence', "
                    "weightage = 10.0, "
                    "display_order = 6 "
                    "WHERE code = 'REQ_3_6'"
                )
            )

        # Ensure REQ_3_COPO exists for backward compatibility
        copo_exists = conn.execute(
            sa.text("SELECT 1 FROM nba_requirements WHERE code = 'REQ_3_COPO'")
        ).fetchone()
        if not copo_exists:
            new_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    "INSERT INTO nba_requirements (id, criterion_id, code, title, description, weightage, is_mandatory, evaluation_rule_key, display_order, created_at, updated_at) "
                    "VALUES (:id, :criterion_id, 'REQ_3_COPO', 'CO-PO Mapping Completeness (Legacy)', 'Legacy requirement for CO-PO mapping completeness verification.', 0.0, 0, 'criterion3.copo_mapping_completeness', 9, :created_at, :updated_at)"
                ),
                {"id": new_id, "criterion_id": c3_id, "created_at": now, "updated_at": now},
            )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 20.0 WHERE code = 'REQ_4_2'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 15.0 WHERE code = 'REQ_4_6'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 35.0 WHERE code = 'REQ_4_7'"
        )
    )

    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 20.0 WHERE code = 'REQ_5_2'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE nba_requirements SET weightage = 15.0 WHERE code = 'REQ_5_5'"
        )
    )
