import psycopg2
import uuid
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Insert plan versions for all 4 plans
# Using the plan_id UUIDs that were previously working
# Need to include effective_from and effective_to
versions_data = [
    ('starter', '86b2eec4-520c-4228-b334-3efcd102e4f0', 1, 299900, 2999000, 30),
    ('growth', 'fa0c5115-02ea-4da4-a16f-7c437ec9a9d6', 3, 599900, 5999000, 25),
    ('professional', '4e74f0b5-edbc-44fe-9539-02177bb7f907', 1, 999900, 9999000, 20),
    ('enterprise', 'e5abdd75-ed9d-43ad-a684-321f6002b06a', 1, 1999900, 19999000, 0),
]

now = datetime.now(UTC)

for code, plan_id, version, price_monthly, price_annual, trial_days in versions_data:
    version_id = str(uuid.uuid4())
    cur.execute('''
        INSERT INTO platform_plan_versions (id, plan_id, version, price_monthly_minor, price_annual_minor, currency_code, trial_days, is_active, effective_from, effective_to, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s, %s, %s, %s)
    ''', (version_id, plan_id, version, price_monthly, price_annual, 'NPR', trial_days, True, now, now, now, now))
    print(f'Inserted: {code} - trial_days={trial_days}')

c.commit()
c.close()
print('\n✅ Plan versions seeded successfully')