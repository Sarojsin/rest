"""Seed one active plan version per active platform plan (clean-DB bootstrap)."""

import psycopg2
from datetime import UTC, datetime

conn = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = conn.cursor()
now = datetime.now(UTC)

cur.execute(
    "SELECT id, code, price_monthly_minor, price_annual_minor, currency_code, trial_days "
    "FROM platform_plans WHERE status = 'ACTIVE' ORDER BY sort_order"
)
plans = cur.fetchall()

for plan_id, code, monthly, annual, currency, trial_days in plans:
    cur.execute(
        "SELECT count(*) FROM platform_plan_versions WHERE plan_id = %s AND is_active = true",
        (plan_id,),
    )
    if cur.fetchone()[0]:
        print(f"skip {code}: active version exists")
        continue
    cur.execute(
        """
        INSERT INTO platform_plan_versions
            (id, plan_id, version, price_monthly_minor, price_annual_minor,
             currency_code, trial_days, effective_from, effective_to, is_active,
             grace_period_days, created_at, updated_at)
        VALUES
            (gen_random_uuid(), %s, 1, %s, %s, %s, %s, %s, NULL, true, 7, %s, %s)
        """,
        (plan_id, monthly, annual, currency, trial_days, now, now, now),
    )
    print(f"seeded {code}: monthly={monthly} annual={annual} trial={trial_days}")

conn.commit()
cur.close()
conn.close()
print("plan version seed complete")
