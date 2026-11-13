"""pa0029_payment_method_qr_cloudinary

Revision ID: pa0029
Revises: pa0028
Create Date: 2026-11-13 00:00:00.000000

Add Cloudinary-backed storage fields for payment method QR images.

QR images were previously stored on the local filesystem, which is ephemeral
on Render and lost on redeploy/restart. These columns allow storing the
Cloudinary public_id and secure_url so images persist across deploys.
Existing local-file columns are kept for backward compatibility.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pa0029"
down_revision = "pa0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_methods",
        sa.Column("qr_image_public_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "payment_methods",
        sa.Column("qr_image_secure_url", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_methods", "qr_image_secure_url")
    op.drop_column("payment_methods", "qr_image_public_id")
