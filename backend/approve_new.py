import psycopg2
import uuid
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, 'E:\\rest\\backend')
from app.core.security import new_token, hash_token

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)
reg_id = '4e0af5c1-dc40-4f22-9789-3610e06b19f2'
owner_email = 'sagardhami84@gmail.com'

# Check registration
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE id = %s", (reg_id,))
reg = cur.fetchone()
print(f'Registration: id={reg[0]}, name={reg[1]}, email={reg[2]}, plan={reg[3]}, status={reg[4]}')

# Get plan
cur.execute("SELECT id, code FROM platform_plans WHERE code = %s AND status = 'ACTIVE' AND is_public = true", (reg[3],))
plan = cur.fetchone()
plan_id = plan[0]
print(f'Plan ID: {plan_id}')

# Get active plan version
cur.execute("SELECT id, price_monthly_minor, currency_code FROM platform_plan_versions WHERE plan_id = %s AND is_active = true ORDER BY version DESC LIMIT 1", (plan_id,))
pv = cur.fetchone()
plan_version_id = pv[0]
print(f'Plan version ID: {pv[0]}, price: {pv[1]} {pv[2]}')

# Generate restaurant ID
restaurant_id = str(uuid.uuid4())
print(f'Restaurant ID: {restaurant_id}')

# Create restaurant
cur.execute("""
    INSERT INTO restaurants
        (id, name, slug, status, timezone, currency_code,
         contact_email, contact_phone, legal_name, created_at, updated_at)
    VALUES
        (%s, %s, %s, 'ACTIVE', 'UTC', 'USD',
         %s, %s, %s, %s, %s)
""",
    (
        restaurant_id,
        reg[1],
        'sagar-test-84',
        owner_email,
        '9820243416',
        'Sagar Dhami',
        now,
        now,
    ),
)
print(f'Restaurant created')

# Create restaurant settings
cur.execute("""
    INSERT INTO restaurant_settings
        (restaurant_id, locale, business_day_start_local, tax_rate_bps,
         receipt_header, receipt_footer, qr_ordering_enabled,
         online_payments_enabled, settings_version, customer_subdomain,
         brand_logo_url, brand_accent_hex, created_at, updated_at)
    VALUES
        (%s, 'en-NP', '05:00', 1300, 'Thank you', true,
         true, false, 1, 'sagar-test-84', '', '', %s, %s)
""",
    (restaurant_id, now, now),
)
print(f'Restaurant settings created')

# Create invited owner (user)
user_id = str(uuid.uuid4())
owner_name = reg[2].split('@')[0]
import hashlib
password_hash = hashlib.sha256(new_token(48).encode()).hexdigest()

cur.execute("""
    INSERT INTO users
        (id, email, password_hash, display_name, status, created_at, updated_at)
    VALUES
        (%s, %s, %s, %s, 'INVITED', %s, %s)
""",
    (
        user_id,
        owner_email,
        password_hash,
        owner_name,
        now,
        now,
    ),
)
print(f'User created: {owner_email}')

# Create membership
membership_id = str(uuid.uuid4())
cur.execute("""
    INSERT INTO restaurant_memberships
        (id, restaurant_id, user_id, role, status, token_version,
         created_at, updated_at)
    VALUES
        (%s, %s, %s, 'owner', 'ACTIVE', 0, %s, %s)
""",
    (membership_id, restaurant_id, user_id, now, now),
)
print(f'Membership created')

# Create subscription
trial_ends_at = now + timedelta(days=25)
cur.execute("""
    INSERT INTO platform_subscriptions
        (id, restaurant_id, plan_id, plan_version_id, status,
         trial_ends_at, current_period_start, current_period_end,
         cancel_at_period_end, price_snapshot_minor, currency_snapshot,
         billing_interval_snapshot, trial_extension_count,
         trial_extension_total_days, created_by_admin_id, created_at, updated_at)
    VALUES
        (%s, %s, %s, %s, 'TRIALING', %s, %s, %s, False,
         5999, 'NPR', 'MONTHLY', 0, 0, NULL, %s, %s)
""",
    (str(uuid.uuid4()), restaurant_id, plan_id, plan_version_id,
     trial_ends_at, now, now + timedelta(days=25), now, now),
)
print(f'Subscription created')

# Create invitation token
raw_token = new_token(32)
token_hash = hash_token(raw_token)
token_uuid = str(uuid.uuid4())

cur.execute(
    "INSERT INTO platform_one_time_tokens (id, token_hash, purpose, email, restaurant_id, expires_at, created_by_admin_id, created_at) VALUES (%s, %s, 'OWNER_INVITE', %s, %s, %s, NULL, %s)",
    (token_uuid, token_hash, owner_email, restaurant_id, now + timedelta(hours=72), now),
)
print(f'\n=== INVITATION TOKEN ===')
print(f'Token: {raw_token}')
print(f'Expires at: {now + timedelta(hours=72)}')

# Update registration
cur.execute("""
    UPDATE self_service_registrations
    SET restaurant_id = %s, status = 'APPROVED',
        reviewed_by_admin_id = NULL, reviewed_at = %s,
        updated_at = %s
    WHERE id = %s
""",
    (restaurant_id, now, now, reg_id),
)
print(f'Registration updated to APPROVED')

c.commit()

invitation_url = f"http://192.168.1.5:5173/auth/invitations/{raw_token}"
print(f'\n=== INVITATION URL ===')
print(f'{invitation_url}')
print(f'\nUse this URL to test owner onboarding.')

cur.close()
c.close()
print('\n=== DONE ===')