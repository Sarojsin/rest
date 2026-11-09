"""Issue a replacement owner-invitation link for Sagar Kitchen.

Restaurant 1 was created before the API began returning ``token`` in the
response, so its raw invitation token exists only in the email. This adds a
second single-use token (same 72h policy) so the link can be delivered to the
owner directly if email did not arrive. The original email link stays valid.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import psycopg2

RESTAURANT_ID = "0c68cc5e-a400-4c27-8ee9-f4e485e5e18b"
EMAIL = "sagardhami84@gmail.com"
BASE_URL = "http://192.168.1.5:5173"

raw = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
now = datetime.now(UTC)
expires = now + timedelta(hours=72)

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute(
    """
    INSERT INTO platform_one_time_tokens
        (id, token_hash, purpose, email, restaurant_id, expires_at,
         created_by_admin_id, created_at)
    VALUES (gen_random_uuid(), %s, 'OWNER_INVITE', %s, %s, %s, NULL, %s)
    """,
    (token_hash, EMAIL, RESTAURANT_ID, expires, now),
)
c.commit()
cur.close()
c.close()

print(f"link: {BASE_URL}/auth/invitations/{raw}")
print(f"expires: {expires.isoformat()}")
