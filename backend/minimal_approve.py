import psycopg2
import uuid
from datetime import UTC, datetime, timedelta
from app.core.security import new_token, hash_token

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)
reg_id = '350db4f9-2f81-445d-ae9e-671a27e10193'
owner_email = 'sagardhami84@gmail.com'

# Generate new restaurant ID
restaurant_id = str(uuid.uuid4())

# Step 1: Create restaurant
cur.execute(
    """
    INSERT INTO restaurants
        (id, name, slug, status, timezone, currency_code,
         contact_email, contact_phone, legal_name, created_at, updated_at)
    VALUES
        (%s, %s, %s, 'ACTIVE', 'UTC', 'USD',
         %s, %s, %s, %s, %s)
    """,
    (
        restaurant_id,
        'Test Restaurant',
        'test-restaurant',
        'UTC',
        'USD',
        owner_email,
        '',
        'Test Legal',
        now,
        now,
    ),
)
print(f'Restaurant created: {restaurant_id}')

# Step 2: Create restaurant settings
cur.execute(
    """
    INSERT INTO restaurant_settings
        (restaurant_id, locale, business_day_start_local, tax_rate_bps,
         receipt_header, receipt_footer, qr_ordering_enabled,
         online_payments_enabled, settings_version, customer_subdomain,
         brand_logo_url, brand_accent_hex, created_at, updated_at)
    VALUES
        (%s, 'en-NP', '05:00', 1300, 'Thank you', true,
         true, false, 1, %s, '', '', %s, %s)
    """,
    (
        restaurant_id,
        restaurant_id,
        now,
        now,
    ),
)
print('Restaurant settings created')

# Step 3: Create invitation token in platform_one_time_tokens
raw_token = new_token(32)
token_hash = hash_token(raw_token)
token_uuid = str(uuid.uuid4())

cur.execute(
    """
    INSERT INTO platform_one_time_tokens
        (id, token_hash, purpose, email, restaurant_id, platform_admin_id, expires_at, used_at, created_by_admin_id, created_at)
    VALUES
        (%s, %s, 'OWNER_INVITE', %s, %s, NULL, %s, NULL, %s, %s)
    """,
    (
        token_uuid,           # -> %s1: id
        token_hash,           # -> %s2: token_hash
        owner_email,          # -> %s3: email (3rd %s)
        restaurant_id,        # -> %s4: restaurant_id
        now + timedelta(hours=72),  # -> %s5: expires_at (this is wrong position - let me recheck)
        str(uuid.uuid4()),    # -> %s6: created_by_admin_id... 
        now,                # -> %s6 or created_at
    ),
)
print(f'Invitation token generated: {raw_token}')

# Oops, I mixed up the execute calls. Let me restart this properly.
print('Need to restart the script approach')

c.close()