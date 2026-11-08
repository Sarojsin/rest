"""pa0017_export_job_creator_nullable

Revision ID: pa0017
Revises: pa0016
Create Date: 2026-11-08 10:50:00.000000

The ``created_by_admin_id`` foreign key already used ``ON DELETE SET NULL``,
but the column was declared ``NOT NULL``. Deleting a platform admin who had
created export jobs therefore failed. Historical export jobs keep their data;
only the creator reference is cleared.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0017"
down_revision = "pa0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "platform_export_jobs",
        "created_by_admin_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "platform_export_jobs",
        "created_by_admin_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
