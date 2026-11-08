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

# Check existing registration
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status, restaurant_id FROM self_service_registrations WHERE owner_email = %s ORDER BY created_at DESC LIMIT 1", (owner_email,))
reg = cur.fetchone()
print(f'Registration: id={reg[0]}, name={reg[1]}, email={reg[2]}, plan={reg[3]}, status={reg[4]}, restaurant_id={reg[5]}')

# Check if user already exists
cur.execute("SELECT id, email, status FROM users WHERE email = %s", (owner_email,))
user = cur.fetchone()
if user:
    print(f'User already exists: id={user[0]}, email={user[1]}, status={user[2]}')
else:
    print('User does not exist yet - will be created on invitation acceptance')

# Generate fresh invitation token
raw_token = new_token(32)
token_hash = hash_token(raw_token)
token_uuid = str(uuid.uuid4())

cur.execute(
    "INSERT INTO platform_one_time_tokens (id, token_hash, purpose, email, restaurant_id, expires_at, created_by_admin_id, created_at) VALUES (%s, %s, 'OWNER_INVITE', %s, %s, %s, NULL, %s)",
    (token_uuid, token_hash, owner_email, reg[5], now + timedelta(hours=72), now),
)

c.commit()

# Verify
cur.execute("SELECT token_hash, purpose, email, restaurant_id, expires_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' AND email = %s ORDER BY created_at DESC LIMIT 1", (owner_email,))
token = cur.fetchone()
print(f'\n=== INVITATION TOKEN CREATED ===')
print(f'Token (full): {raw_token}')
print(f'Expires at: {token[4]}')

# Construct invitation URL
invitation_url = f"http://192.168.1.5:5173/auth/invitations/{raw_token}"
print(f'\n=== INVITATION URL ===')
print(f'{invitation_url}')

cur.close()
c.close()