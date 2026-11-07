import psycopg2
import uuid
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, 'E:\\rest\\backend')
from app.core.security import new_token, hash_token

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)
reg_id = '6403e03c-ed54-4723-9d54-2e1b374490cd'
owner_email = 'sagardhami84@gmail.com'

# Check registration
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE id = %s", (reg_id,))
reg = cur.fetchone()
print(f'Registration: {reg[1]} - {reg[2]} - {reg[3]} - {reg[4]}')

# Use existing Harbor Table restaurant ID
existing_restaurant_id = 'd6dc926e-8638-43b3-9458-965141acd192'

# Generate token (this is what happens during approval)
raw_token = new_token(32)
token_hash = hash_token(raw_token)

# Insert invitation token
token_uuid = str(uuid.uuid4())
cur.execute(
    "INSERT INTO platform_one_time_tokens (id, token_hash, purpose, email, restaurant_id, expires_at, created_by_admin_id, created_at) VALUES (%s, %s, 'OWNER_INVITE', %s, %s, %s, NULL, %s)",
    (token_uuid, token_hash, owner_email, existing_restaurant_id, now + timedelta(hours=72), now),
)
print(f'Token generated: {raw_token[:20]}...')

# Update registration - use existing restaurant ID, NULL for reviewed_by_admin_id
cur.execute(
    "UPDATE self_service_registrations SET restaurant_id = %s, status = 'APPROVED', reviewed_by_admin_id = NULL, reviewed_at = %s, updated_at = %s WHERE id = %s",
    (existing_restaurant_id, now, now, reg_id),
)

c.commit()

# Verify
cur.execute("SELECT token_hash, purpose, email, restaurant_id, expires_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' ORDER BY created_at DESC LIMIT 1")
token = cur.fetchone()
print(f'Verified token for: {token[2] if token else None}')
print(f'Expires at: {token[4] if token else None}')
print(f'Restaurant ID: {token[3] if token else None}')

cur.close()
c.close()
print('\n--- DONE ---')
print('Check Gmail at sagardhami84@gmail.com for invitation email')
print('Owner clicks invitation link to complete onboarding')