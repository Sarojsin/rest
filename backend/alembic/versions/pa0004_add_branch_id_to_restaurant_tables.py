"""PA-0.12: add branch_id to restaurant_tables

Revision ID: pa0004
Revises: pa0003tenantlifecycle
Create Date: 2026-11-04 16:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "pa0004"
down_revision: Union[str, Sequence[str], None] = "pa0003tenantlifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "restaurant_tables",
        sa.Column(
            "branch_id",
            postgresql.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_foreign_key(
        "fk_restaurant_tables_branch_id_restaurants",
        "restaurant_tables",
        "restaurants",
        ["branch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_restaurant_tables_branch_id_restaurants", "restaurant_tables", type_="foreignkey")
    op.drop_column("restaurant_tables", "branch_id")