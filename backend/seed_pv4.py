import psycopg2
import uuid
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)

# Insert plan versions
pvs = [
    ('86b2eec4-520c-4228-b334-3efcd102e4f0', 1, 1, 299900, 2999000, 30, 'starter'),
    ('fa0c5115-02ea-4da4-a16f-7c437ec9a9d6', 3, 3, 599900, 5999000, 25, 'growth'),
    ('4e74f0b5-edbc-44fe-9539-02177bb7f907', 1, 1, 999900, 9999000, 20, 'professional'),
    ('e5abdd75-ed9d-43ad-a684-321f6002b06a', 1, 1, 1999900, 19999000, 0, 'enterprise'),
]

for items in pvs:
    plan_id, version, price_monthly, price_annual, trial_days, code = items[:6]
    vid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO platform_plan_versions (id, plan_id, version, price_monthly_minor, price_annual_minor, currency_code, trial_days, is_active, effective_from, effective_to, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s, %s, %s, %s)",
        (vid, plan_id, version, price_monthly, price_annual, 'NPR', trial_days, now, now, now, now)
    )
    print(f'Inserted: {code}')

c.commit()
c.close()
print('Done seeding plan versions')