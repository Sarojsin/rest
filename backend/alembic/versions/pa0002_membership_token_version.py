"""PA-0.10: staff membership token version for force logout

Revision ID: pa0002membershiptoken
Revises: pa0001platformidentity
Create Date: 2026-11-04

Adds ``restaurant_memberships.token_version``. Staff access tokens carry a
``ver`` claim; a mismatch is rejected as ``TOKEN_REVOKED``. Existing rows and
tokens are treated as version 0, so deployment does not log everyone out.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0002membershiptoken"
down_revision: Union[str, Sequence[str], None] = "pa0001platformidentity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "restaurant_memberships",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("restaurant_memberships", "token_version")
