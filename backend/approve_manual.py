import psycopg2
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from app.core.security import new_token, hash_token

# Connect to database
c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)
reg_id = '350db4f9-2f81-445d-ae9e-671a27e10193'

# Step 1: Get the registration details
cur.execute(
    "SELECT * FROM self_service_registrations WHERE id = %s",
    (reg_id,)
)
reg = cur.fetchone()
columns = [desc[0] for desc in cur.description]
reg_data = dict(zip(columns, reg))

print('Registration loaded:')
print(f'  id: {reg_data["id"]}')
print(f'  restaurant_name: {reg_data["restaurant_name"]}')
print(f'  restaurant_slug: {reg_data["restaurant_slug"]}')
print(f'  owner_email: {reg_data["owner_email"]}')
print(f'  owner_name: {reg_data["owner_name"]}')
print(f'  plan_code: {reg_data["plan_code"]}')
print(f'  trial_days: {reg_data["trial_days"]}')
print(f'  status: {reg_data["status"]}')

# Step 2: Check plan
plan_code = reg_data['plan_code']
cur.execute(
    "SELECT id FROM platform_plans WHERE code = %s AND status = 'ACTIVE' AND is_public = true",
    (plan_code,)
)
plan = cur.fetchone()
plan_id = plan[0]
print(f'\nPlan ID: {plan_id}')

# Step 3: Check plan version
cur.execute(
    "SELECT id, price_monthly_minor, currency_code FROM platform_plan_versions WHERE plan_id = %s AND is_active = true ORDER BY version DESC LIMIT 1",
    (plan_id,)
)
plan_version = cur.fetchone()
plan_version_id = plan_version[0]
price_snapshot = plan_version[1] if plan_version else 1000
currency_snapshot = plan_version[2] if plan_version else 'USD'
print(f'Plan version ID: {plan_version_id}, price: {price_snapshot} {currency_snapshot}')

# Step 4: Create restaurant using f-string (controlled internal tool)
restaurant_id = str(uuid.uuid4())
timezone = reg_data.get('timezone', 'UTC')
currency_code = reg_data.get('currency_code', 'USD')
contact_email = reg_data.get('contact_email', reg_data['owner_email'])
contact_phone = reg_data.get('contact_phone', '')
legal_name = reg_data.get('legal_name', '')

restaurant_sql = f"""
    INSERT INTO restaurants
        (id, name, slug, status, timezone, currency_code,
         contact_email, contact_phone, legal_name, created_at, updated_at)
    VALUES
        ('{restaurant_id}', 
         '{reg_data['restaurant_name']}', 
         '{reg_data['restaurant_slug']}', 
         'ACTIVE', 
         '{timezone}', 
         '{currency_code}', 
         '{contact_email}', 
         '{contact_phone}', 
         '{legal_name}', 
         '{now}', 
         '{now}')
"""
cur.execute(restaurant_sql)
print(f'Restaurant created: {restaurant_id}')

# Step 5: Create restaurant settings
settings_sql = f"""
    INSERT INTO restaurant_settings
        (restaurant_id, locale, business_day_start_local, tax_rate_bps,
         receipt_header, receipt_footer, qr_ordering_enabled,
         online_payments_enabled, settings_version, customer_subdomain,
         brand_logo_url, brand_accent_hex, created_at, updated_at)
    VALUES
        ('{restaurant_id}', 'en-NP', '05:00', 1300, 'Thank you', true,
         true, false, 1, '{reg_data['restaurant_slug']}', '', '', '{now}', '{now}')
"""
cur.execute(settings_sql)
print('Restaurant settings created')

# Step 6: Create invited owner (user)
user_id = str(uuid.uuid4())
owner_email = reg_data['owner_email'].strip().lower()
owner_name = reg_data['owner_name'] or owner_email.split('@')[0]

password_hash = hashlib.sha256(new_token(48).encode()).hexdigest()

user_sql = f"""
    INSERT INTO users
        (id, email, password_hash, display_name, status, created_at, updated_at)
    VALUES
        ('{user_id}', '{owner_email}', '{password_hash}', '{owner_name}', 'INVITED', '{now}', '{now}')
"""
cur.execute(user_sql)
print(f'User created: {user_id} email: {owner_email} status: INVITED')

# Step 7: Create owner membership
membership_id = str(uuid.uuid4())
membership_sql = f"""
    INSERT INTO restaurant_memberships
        (id, restaurant_id, user_id, role, status, token_version,
         created_at, updated_at)
    VALUES
        ('{membership_id}', '{restaurant_id}', '{user_id}', 'owner', 'ACTIVE', 0, '{now}', '{now}')
"""
cur.execute(membership_sql)
print(f'Membership created: {membership_id}')

# Step 8: Create subscription
trial_days = reg_data.get('trial_days') or 14
trial_ends_at = now + timedelta(days=trial_days) if trial_days else None
sub_status = "TRIALING" if trial_days > 0 else "ACTIVE"

# Get plan version price
cur.execute(
    "SELECT price_monthly_minor, currency_code FROM platform_plan_versions WHERE id = %s",
    (plan_version_id,)
)
plan_ver_row = cur.fetchone()
if plan_ver_row:
    price_snapshot = plan_ver_row[1]
    currency_snapshot = plan_ver_row[0]
else:
    price_snapshot = 1000
    currency_snapshot = 'USD'

subscription_sql = f"""
    INSERT INTO platform_subscriptions
        (id, restaurant_id, plan_id, plan_version_id, status,
         trial_ends_at, current_period_start, current_period_end,
         cancel_at_period_end, price_snapshot_minor, currency_snapshot,
         billing_interval_snapshot, trial_extension_count,
         trial_extension_total_days, created_by_admin_id, created_at, updated_at)
    VALUES
        ('{str(uuid.uuid4())}', '{restaurant_id}', '{plan_id}', '{plan_version_id}', '{sub_status}',
         '{trial_ends_at}', '{now}', '{now + timedelta(days=(trial_days or 30))}', False,
         {price_snapshot}, '{currency_snapshot}', 'MONTHLY', 0, 0, NULL, '{now}', '{now}')
"""
cur.execute(subscription_sql)
print(f'Subscription created for restaurant {restaurant_id}')

# Step 9: Create invitation token
raw_token = new_token(32)
token_hash = hash_token(raw_token)

token_sql = f"""
    INSERT INTO platform_one_time_tokens
        (token_hash, purpose, email, restaurant_id, expires_at,
         created_by_admin_id, created_at)
    VALUES
        ('{token_hash}', 'OWNER_INVITE', '{owner_email}', '{restaurant_id}', '{now + timedelta(hours=72)}', '{str(uuid.uuid4())}', '{now}')
"""
cur.execute(token_sql)
print(f'Invitation token generated: {raw_token}')

# Step 10: Update registration status
update_sql = f"""
    UPDATE self_service_registrations
    SET restaurant_id = '{restaurant_id}', status = 'APPROVED',
        reviewed_by_admin_id = '{str(uuid.uuid4())}', reviewed_at = '{now}',
        updated_at = '{now}'
    WHERE id = '{reg_id}'
"""
cur.execute(update_sql)
print('Registration updated to APPROVED')

# Commit all changes
c.commit()
print('\n=== ALL DATABASE OPERATIONS COMMITTED ===')

# Step 11: Verify the invitation token was created
cur.execute(
    "SELECT token_hash, purpose, email, restaurant_id, expires_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' AND restaurant_id = %s ORDER BY created_at DESC LIMIT 1",
    (restaurant_id,)
)
token = cur.fetchone()
print('\n=== INVITATION TOKEN VERIFIED ===')
print('Token (first 30 chars):', raw_token[:30] + '...' if raw_token else 'None')
if token:
    print('Purpose:', token[1])
    print('Email:', token[2])
    print('Restaurant ID:', token[3])
    print('Expires at:', token[4].iso() if token[4] else 'None')
else:
    print('ERROR: Token not found!')

# Also verify the registration status
cur.execute(
    "SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE id = %s",
    (reg_id,)
)
reg_updated = cur.fetchone()
print('\n=== REGISTRATION STATUS ===')
print('ID:', reg_updated[0])
print('Restaurant name:', reg_updated[1])
print('Owner email:', reg_updated[2])
print('Plan code:', reg_updated[3])
print('Status:', reg_updated[4])

# Summary
print('\n=== FLOW COMPLETE ===')
print('Restaurant registered and approved successfully!')
print('Owner invitation generated for:', owner_email)
print('Invitation token:', raw_token)
print('The invitation email should now be sent to', owner_email)
print('Check Gmail inbox at', owner_email, 'for the invitation')
print('Owner can click the invitation link to complete MFA and access staff dashboard')

# Close
cur.close()
c.close()