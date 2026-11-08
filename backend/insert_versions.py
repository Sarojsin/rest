import psycopg2
import uuid
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check current state
cur.execute("SELECT id, code FROM platform_plans WHERE is_public = true AND status = 'ACTIVE'")
plans = cur.fetchall()
print(f'Plans: {plans}')

cur.execute("SELECT count(*) FROM platform_plan_versions")
count = cur.fetchone()
print(f'Plan versions count: {count[0]}')

# Insert plan versions if empty
if count[0] == 0:
    now = datetime.now(UTC)
    version_data = [
        (plans[0][0], 1, 30, 299900, 2999000, 'NPR', True),
        (plans[1][0], 3, 25, 599900, 5999000, 'NPR', True),
        (plans[2][0], 1, 20, 999900, 9999000, 'NPR', True),
        (plans[3][0], 1, 0, 1999900, 19999000, 'NPR', True),
    ]
    for plan_id, version, trial_days, price_monthly, price_annual, currency, is_active in version_data:
        version_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO platform_plan_versions
                (id, plan_id, version, price_monthly_minor, price_annual_minor,
                 currency_code, trial_days, is_active, effective_from, created_at, updated_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (version_id, plan_id, version, price_monthly, price_annual,
              currency, trial_days, is_active, now, now, now))
        print(f'Inserted version {version} for plan {plan_id[:8]}...')
    c.commit()
    print('All plan versions inserted')

# Verify
cur.execute("SELECT plan_id, version, is_active, trial_days FROM platform_plan_versions ORDER BY plan_id, version")
for r in cur.fetchall():
    print(f'  plan_id={r[0][:8]}..., version={r[1]}, active={r[2]}, trial_days={r[3]}')

cur.close()
c.close()