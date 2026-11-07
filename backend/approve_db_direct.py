import psycopg2
import uuid
from datetime import UTC, datetime, timedelta

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)
reg_id = '6403e03c-ed54-4723-9d54-2e1b374490cd'
owner_email = 'sagardhami84@gmail.com'

# Check if registration exists
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE id = %s", (reg_id,))
reg = cur.fetchone()
print(f'Registration found: {reg is not None}')
if reg:
    print(f'  id={reg[0]}, name={reg[1]}, email={reg[2]}, plan={reg[3]}, status={reg[4]}')

# Check if already approved
if reg and reg[4] == 'APPROVED':
    print('  Already approved!')
    c.close()
    exit(0)

# Generate restaurant ID
restaurant_id = uuid.uuid4()
restaurant_id_str = str(restaurant_id)
print(f'\nGenerating restaurant ID: {restaurant_id_str}')

# Create restaurant - use .format() instead of f-string with %s
restaurant_sql = """INSERT INTO restaurants
    (id, name, slug, status, timezone, currency_code,
     contact_email, contact_phone, legal_name, created_at, updated_at)
 VALUES
    ('{rid}', 'Test Restaurant', 'test-restaurant', 'UTC', 'USD',
     '{owner_email}', '', 'Test Legal', '{now}', '{now}')""".format(
    rid=restaurant_id_str,
    owner_email=owner_email,
    now=now
)
cur.execute(restaurant_sql)
print(f'Restaurant created: {restaurant_id_str}')

# Create restaurant settings
settings_sql = """INSERT INTO restaurant_settings
    (restaurant_id, locale, business_day_start_local, tax_rate_bps,
     receipt_header, receipt_footer, qr_ordering_enabled,
     online_payments_enabled, settings_version, customer_subdomain,
     brand_logo_url, brand_accent_hex, created_at, updated_at)
 VALUES
    ('{rid}', 'en-NP', '05:00', 1300, 'Thank you', true,
     true, false, 1, '{slug}', '', '', '{now}', '{now}')""".format(
    rid=restaurant_id_str,
    slug='test-restaurant',
    now=now
)
cur.execute(settings_sql)
print('Restaurant settings created')

# Create user (owner)
user_id = uuid.uuid4()
user_id_str = str(user_id)
password_hash = 'hash_test_password'

user_sql = """INSERT INTO users
    (id, email, password_hash, display_name, status, created_at, updated_at)
 VALUES
    ('{uid}', '{email}', '{pw}', '{display}', 'INVITED', '{now}', '{now}')""".format(
    uid=user_id_str,
    email=owner_email,
    pw=password_hash,
    display=owner_email.split('@')[0],
    now=now
)
cur.execute(user_sql)
print(f'User created: {user_id_str}')

# Create membership
membership_id = uuid.uuid4()
membership_id_str = str(membership_id)

membership_sql = """INSERT INTO restaurant_memberships
    (id, restaurant_id, user_id, role, status, token_version,
     created_at, updated_at)
 VALUES
    ('{mid}', '{rid}', '{uid}', 'owner', 'ACTIVE', 0, '{now}', '{now}')""".format(
    mid=membership_id_str,
    rid=restaurant_id_str,
    uid=user_id_str,
    now=now
)
cur.execute(membership_sql)
print(f'Membership created: {membership_id_str}')

# Create subscription
trial_ends_at = now + timedelta(days=14)
subscription_sql = """INSERT INTO platform_subscriptions
    (id, restaurant_id, plan_id, plan_version_id, status,
     trial_ends_at, current_period_start, current_period_end,
     cancel_at_period_end, price_snapshot_minor, currency_snapshot,
     billing_interval_snapshot, trial_extension_count,
     trial_extension_total_days, created_by_admin_id, created_at, updated_at)
 VALUES
    ('{sid}', '{rid}', '{pid}', '{pvid}', 'TRIALING',
     '{trial_ends}', '{now}', '{now_plus_14}', False,
     5999, 'NPR', 'MONTHLY', 0, 0, NULL, '{now}', '{now}')""".format(
    sid=str(uuid.uuid4()),
    rid=restaurant_id_str,
    pid='fe736ba2-bccd-44d5-ac0d-8fe98a787f94',  # growth plan
    pvid='fbe4ac5c-6291-4ad1-b470-570d62783bdd',  # plan version
    trial_ends=trial_ends_at,
    now_plus_14=now + timedelta(days=14),
    now=now
)
cur.execute(subscription_sql)
print('Subscription created')

# Create invitation token
raw_token = 'temp-token-' + str(uuid.uuid4())[:8]
token_hash = 'hash_' + raw_token

token_sql = """INSERT INTO platform_one_time_tokens
    (id, token_hash, purpose, email, restaurant_id, expires_at,
     created_by_admin_id, created_at)
 VALUES
    ('{tid}', '{th}', 'OWNER_INVITE', '{email}', '{rid}', '{expires}',
     '{admin}', '{now}')""".format(
    tid=str(uuid.uuid4()),
    th=token_hash,
    email=owner_email,
    rid=restaurant_id_str,
    expires=now + timedelta(hours=72),
    admin=str(uuid.uuid4()),
    now=now
)
cur.execute(token_sql)
print(f'Invitation token created: {raw_token}')

# Update registration status
update_sql = """UPDATE self_service_registrations
 SET restaurant_id = '{rid}', status = 'APPROVED',
     reviewed_by_admin_id = '{admin}', reviewed_at = '{now}',
     updated_at = '{now}'
 WHERE id = '{reg_id}'""".format(
    rid=restaurant_id_str,
    admin=str(uuid.uuid4()),
    now=now,
    reg_id=reg_id
)
cur.execute(update_sql)
print('Registration updated to APPROVED')

c.commit()
print('\n=== ALL CHANGES COMMITTED ===')

# Verify
print('\n=== VERIFICATION ===')
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE id = %s", (reg_id,))
reg_updated = cur.fetchone()
print(f'Registration: id={reg_updated[0]}, name={reg_updated[1]}, email={reg_updated[2]}, plan={reg_updated[3]}, status={reg_updated[4]}')

cur.execute("SELECT token_hash, purpose, email, restaurant_id, expires_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' ORDER BY created_at DESC LIMIT 1")
token = cur.fetchone()
if token:
    print(f'Token: {token[1][:20]}... for {token[2]}')
    print(f'Expires: {token[4]}')

cur.close()
c.close()
print('\n=== DONE ===')
print('Owner should now receive invitation email at sagardhami84@gmail.com')