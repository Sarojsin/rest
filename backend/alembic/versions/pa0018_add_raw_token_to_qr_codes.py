"""pa0018_add_raw_token_to_qr_codes

Revision ID: pa0018
Revises: pa0017
Create Date: 2026-11-08 10:55:00.000000

Add ``raw_token`` column to ``table_qr_codes`` so the full QR invitation token
can be returned from the list API. Previously only ``token_preview`` (first 16
chars) was returned, which could not be verified by ``resolve_qr`` because it
hashes the full token. Existing rows get their QR tokens regenerated so the
stored hash matches the returned raw token.
"""

from __future__ import annotations

import uuid
import hashlib

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0018"
down_revision = "pa0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "table_qr_codes",
        sa.Column("raw_token", sa.String(64), nullable=True),
    )

    # Regenerate QR tokens for existing active rows so raw_token matches
    # token_hash. We cannot recover the original raw token from its hash, so
    # each active QR code gets a new random token.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id FROM table_qr_codes WHERE status = 'ACTIVE'")
    ).fetchall()
    for (row_id,) in rows:
        raw = uuid.uuid4().hex  # 32-char hex token
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        conn.execute(
            sa.text(
                "UPDATE table_qr_codes SET raw_token = :raw, token_hash = :hash, "
                "token_preview = :preview WHERE id = :id"
            ),
            {
                "raw": raw,
                "hash": token_hash,
                "preview": raw[:16],
                "id": row_id,
            },
        )


def downgrade() -> None:
    op.drop_column("table_qr_codes", "raw_token")
