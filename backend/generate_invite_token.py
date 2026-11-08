import psycopg2
import uuid
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, 'E:\\rest\\backend')
from app.core.security import new_token, hash_token

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)
owner_email = 'sagardhami84@gmail.com'

# Use existing Harbor Table restaurant
restaurant_id = 'd6dc926e-8638-43b3-9458-965141acd192'

# Check if registration exists and is APPROVED
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE owner_email = %s", (owner_email,))
reg = cur.fetchone()
print(f'Registration: {reg[0]} - {reg[1]} - {reg[2]} - status: {reg[4]}')

# Generate fresh invitation token
raw_token = new_token(32)
token_hash = hash_token(raw_token)
token_uuid = str(uuid.uuid4())

# Insert invitation token
cur.execute(
    "INSERT INTO platform_one_time_tokens (id, token_hash, purpose, email, restaurant_id, expires_at, created_by_admin_id, created_at) VALUES (%s, %s, 'OWNER_INVITE', %s, %s, %s, NULL, %s)",
    (token_uuid, token_hash, owner_email, restaurant_id, now + timedelta(hours=72), now),
)

c.commit()

# Verify
cur.execute("SELECT token_hash, purpose, email, restaurant_id, expires_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' AND email = %s ORDER BY created_at DESC LIMIT 1", (owner_email,))
token = cur.fetchone()
print(f'\n=== INVITATION TOKEN CREATED ===')
print(f'Token (full): {raw_token}')
print(f'Token (first 20): {raw_token[:20]}...')
print(f'Purpose: {token[1]}')
print(f'Email: {token[2]}')
print(f'Restaurant ID: {token[3]}')
print(f'Expires at: {token[4]}')

# Construct invitation URL
invitation_url = f"http://192.168.1.5:5173/auth/invitations/{raw_token}"
print(f'\n=== INVITATION URL ===')
print(f'{invitation_url}')

cur.close()
c.close()
print('\n=== DONE ===')
print('Owner should now be able to click this link to accept the invitation')