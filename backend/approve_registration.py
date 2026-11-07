import psycopg2
from uuid import UUID, uuid4
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# First, let's check the registration details again
reg_id = UUID('350db4f9-2f81-445d-ae9e-671a27e10193')
cur.execute(
    "SELECT * FROM self_service_registrations WHERE id = %s",
    (reg_id,)
)
reg = cur.fetchone()
print('Registration details:')
print('  id:', reg[0])
print('  restaurant_name:', reg[1])
print('  restaurant_slug:', reg[2])
print('  owner_email:', reg[3])
print('  plan_code:', reg[4])
print('  status:', reg[5])
print('  invitation_token_hash:', reg[6])
print('  contact_email:', reg[7])
print('  owner_name:', reg[8])
print('  owner_phone:', reg[9])
print('  created_at:', reg[10])

# Now let's try to approve it
# We need: admin_id, reason
# Let's use the owner@harbor.example as the admin
admin_id = UUID('0c5b5c85-aacd-4175-924e-6d94a22908d9')
reason = "Self-service registration approval"

# Call the approve function logic
from sqlalchemy import text

# Check plan
plan = cur.execute(
    text("SELECT id, code FROM platform_plans WHERE code = 'growth' AND status = 'ACTIVE' AND is_public = true"),
    ()
).fetchone()
print('\nPlan found:', plan)

# Check plan version
plan_version = cur.execute(
    text("SELECT id FROM platform_plan_versions WHERE plan_id = %s AND is_active = true ORDER BY version DESC LIMIT 1"),
    (plan[0],)
).fetchone()
print('Plan version found:', plan_version)

# Check slug availability
slug_exists = cur.execute(
    text("SELECT 1 FROM restaurants WHERE slug = 'random'"),
    ()
).fetchone()
print('Slug exists:', slug_exists)

# Since the registration is PENDING and slug wasn't used yet (restaurant wasn't created),
# let's proceed with approval

# Create restaurant
restaurant_id = uuid4()
now = datetime.now(UTC)

cur.execute(
    text("""
        INSERT INTO restaurants
            (id, name, slug, status, timezone, currency_code,
             contact_email, contact_phone, legal_name, created_at, updated_at)
        VALUES
            (:id, :name, :slug, 'ACTIVE', :timezone, :currency_code,
             :contact_email, :contact_phone, :legal_name, :now, :now)
    """),
    {
        "id": restaurant_id,
        "name": reg[1],  # restaurant_name
        "slug": reg[2],  # restaurant_slug
        "timezone": reg[10],  # timezone - need to get this
        "currency_code": reg[11],  # currency_code - need to get this
        "contact_email": reg[7],  # contact_email
        "contact_phone": reg[8],  # contact_phone
        "legal_name": reg[9],  # legal_name - need to get this
        "now": now,
    },
)

print('\nRestaurant created:', restaurant_id)

# Create user (owner)
user_id = uuid4()
password_hash = 'hash_me'  # In real code, use hash_password

cur.execute(
    text("""
        INSERT INTO users
            (id, email, password_hash, display_name, status, created_at, updated_at)
        VALUES
            (:id, :email, :password_hash, :display_name, 'INVITED', :now, :now)
    """),
    {
        "id": user_id,
        "email": reg[3],  # owner_email
        "password_hash": password_hash,
        "display_name": reg[1].split('@')[0] if '@' in reg[1] else reg[1],
        "now": now,
    },
)

print('User created:', user_id)

# Create membership
membership_id = uuid4()
cur.execute(
    text("""
        INSERT INTO restaurant_memberships
            (id, restaurant_id, user_id, role, status, token_version,
             created_at, updated_at)
        VALUES
            (:id, :rid, :uid, 'owner', 'ACTIVE', 0, :now, :now)
    """),
    {
        "id": membership_id,
        "rid": restaurant_id,
        "uid": user_id,
        "now": now,
    },
)

print('Membership created:', membership_id)

# Create subscription
# Need plan_id and plan_version_id
cur.execute(
    text("""
        INSERT INTO platform_subscriptions
            (id, restaurant_id, plan_id, plan_version_id, status,
             trial_ends_at, current_period_start, current_period_end,
             cancel_at_period_end, price_snapshot_minor, currency_snapshot,
             billing_interval_snapshot, created_by_admin_id, created_at, updated_at)
        VALUES
            (:id, :rid, :pid, :pvid, :status, :trial_ends_at,
             :cps, :cpe, :cancel_at_period_end, :price_snapshot,
             :currency_snapshot, :billing_interval, NULL, :now, :now)
    """),
    {
        "id": uuid4(),
        "rid": restaurant_id,
        "pid": plan[0],
        "pvid": plan_version[0],
        "status": "TRIALING",
        "trial_ends_at": now,  # Will be set based on trial_days
        "cps": now,
        "cpe": now,
        "cancel_at_period_end": False,
        "price_snapshot": 1000,  # Default
        "currency_snapshot": "USD",
        "billing_interval": "MONTHLY",
        "now": now,
    },
)

print('Subscription created')

# Create invitation token
from app.core.security import new_token, hash_token
raw_token = new_token(32)
token_hash = hash_token(raw_token)

cur.execute(
    text("""
        INSERT INTO platform_one_time_tokens
            (token_hash, purpose, email, restaurant_id, expires_at,
             created_by_admin_id, created_at)
        VALUES
            (:token_hash, 'OWNER_INVITE', :email, :rid, :expires_at,
             :admin_id, :now)
    """),
    {
        "token_hash": token_hash,
        "email": reg[3],  # owner_email
        "rid": restaurant_id,
        "expires_at": now,
        "admin_id": admin_id,
        "now": now,
    },
)

print('Invitation token created:', raw_token)

# Update registration
cur.execute(
    text("""
        UPDATE self_service_registrations
        SET restaurant_id = :rid, status = 'APPROVED',
            reviewed_by_admin_id = :admin_id, reviewed_at = :now,
            updated_at = :now
        WHERE id = :reg_id
    """),
    {
        "rid": restaurant_id,
        "admin_id": admin_id,
        "now": now,
        "reg_id": reg_id,
    },
)

c.commit()

# Now get the token info
cur.execute(
    text("SELECT token_hash, purpose, email, restaurant_id, expires_at, created_by_admin_id FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' AND restaurant_id = %s ORDER BY created_at DESC LIMIT 1"),
    (restaurant_id,)
)
token = cur.fetchone()
print('\nInvitation token details:')
print('  token_hash:', token[0][:20] + '...' if token[0] else None)
print('  purpose:', token[1])
print('  email:', token[2])
print('  restaurant_id:', token[3])
print('  expires_at:', token[4])
print('  created_by_admin_id:', token[5])

# Show the full flow result
print('\n=== FLOW COMPLETE ===')
print('Registration approved!')
print('Restaurant created with ID:', restaurant_id)
print('Owner user created with ID:', user_id)
print('Invitation token generated for:', reg[3])
print('Owner can now click the invitation link to complete onboarding')

c.close()