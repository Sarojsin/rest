import psycopg2
import uuid
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Get plan IDs
print("=== Plan IDs ===")
cur.execute("SELECT id, code FROM platform_plans WHERE is_public = true AND status = 'ACTIVE'")
plans = cur.fetchall()
for p in plans:
    print(f"  {p[1]}: id={p[0]}")

# Insert plan versions for each plan
# Based on the API data we saw earlier:
# - starter: trial_days=30, price 299900 annual, version 1
# - growth: trial_days=25, price 599900 annual, version 3
# - professional: trial_days=20
# - enterprise: trial_days=0

now = datetime.now(UTC)

version_data = [
    # plan_id, version, trial_days, price_monthly, price_annual, currency, is_active
    (plans[0][0], 1, 30, 299900, 2999000, 'NPR', True),
    (plans[1][0], 3, 25, 599900, 5999000, 'NPR', True),
    (plans[2][0], 1, 20, 999900, 9999000, 'NPR', True),
    (plans[3][0], 1, 0, 1999900, 19999000, 'NPR', True),
]

for plan_id, version, trial_days, price_monthly, price_annual, currency, is_active in version_data:
    # Check if version already exists
    cur.execute("SELECT id FROM platform_plan_versions WHERE plan_id = %s AND version = %s", (plan_id, version))
    if cur.fetchone():
        print(f"  Version {version} already exists for plan {plan_id}, skipping")
        continue
    
    # Generate UUID for the version
    version_id = str(uuid.uuid4())
    
    cur.execute("""
        INSERT INTO platform_plan_versions
            (id, plan_id, version, price_monthly_minor, price_annual_minor, 
             currency_code, trial_days, is_active, effective_from, created_at, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        version_id,
        plan_id,
        version,
        price_monthly,
        price_annual,
        currency,
        trial_days,
        is_active,
        now,
        now,
        now,
    ))
    print(f"  Inserted version {version} for plan {plan_id[:8]}... (is_active={is_active})")

c.commit()

# Verify
print("\n=== Verify plan versions ===")
cur.execute("SELECT id, plan_id, version, is_active, trial_days FROM platform_plan_versions ORDER BY plan_id, version")
for r in cur.fetchall():
    print(f"  plan_id={r[1][:8]}..., version={r[2]}, is_active={r[3]}, trial_days={r[4]}")

c.close()
print("\n=== Done ===")