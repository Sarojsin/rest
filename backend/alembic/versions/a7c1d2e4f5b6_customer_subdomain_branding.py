"""phase 7 M7: customer subdomain + branding columns

Revision ID: a7c1d2e4f5b6
Revises: ed02e9ab12e0
Create Date: 2026-11-03

Adds the customer-surface config that lives on restaurant_settings per
plan 07 (webplan/07-customer-subdomain.md): locked-at-launch subdomain
label (D5), optional custom domain, and QR-surface branding fields.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1d2e4f5b6"
down_revision: Union[str, Sequence[str], None] = "ed02e9ab12e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "restaurant_settings",
        sa.Column("customer_subdomain", sa.String(length=63), nullable=True),
    )
    op.add_column(
        "restaurant_settings",
        sa.Column("custom_domain", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "restaurant_settings",
        sa.Column("brand_logo_url", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "restaurant_settings",
        sa.Column("brand_accent_hex", sa.String(length=9), nullable=False, server_default=""),
    )
    op.create_unique_constraint(
        "uq_restaurant_settings_customer_subdomain",
        "restaurant_settings",
        ["customer_subdomain"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_restaurant_settings_customer_subdomain", "restaurant_settings", type_="unique"
    )
    op.drop_column("restaurant_settings", "brand_accent_hex")
    op.drop_column("restaurant_settings", "brand_logo_url")
    op.drop_column("restaurant_settings", "custom_domain")
    op.drop_column("restaurant_settings", "customer_subdomain")
