import psycopg2
import uuid
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

now = datetime.now(UTC)

# Insert plan versions using correct plan_id from platform_plans table
pvs = [
    ('692f4dcc-4533-4dfe-9765-aed678a59b43', 1, 299900, 2999000, 30, 'starter'),
    ('7fe05663-ff47-48e6-85da-5aedd2097a15', 3, 599900, 5999000, 25, 'growth'),
    ('8f3e777c-bf9e-4543-8624-b69b9ba8d5f6', 1, 999900, 9999000, 20, 'professional'),
    ('8f7f13bc-c940-404e-8caf-04489f93661d', 1, 1999900, 19999000, 0, 'enterprise'),
]

for plan_id, version, price_monthly, price_annual, trial_days, code in pvs:
    vid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO platform_plan_versions (id, plan_id, version, price_monthly_minor, price_annual_minor, currency_code, trial_days, is_active, effective_from, effective_to, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s, %s, %s, %s)",
        (vid, plan_id, version, price_monthly, price_annual, 'NPR', trial_days, now, now, now, now)
    )
    print(f'Inserted: {code}')

c.commit()
c.close()
print('Done seeding plan versions')