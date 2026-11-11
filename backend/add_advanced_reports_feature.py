import psycopg2
from uuid import uuid4
from datetime import UTC, datetime

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

# Find active plan versions
cur.execute("""
    SELECT pv.id, p.code
    FROM platform_plan_versions pv
    JOIN platform_plans p ON p.id = pv.plan_id
    WHERE pv.is_active = true
    ORDER BY p.code
""")
plan_versions = cur.fetchall()
print("Active plan versions:")
for pv_id, plan_code in plan_versions:
    print(f"  {plan_code}: {pv_id}")

# Check if advanced_reports feature already exists
cur.execute("SELECT DISTINCT plan_version_id FROM platform_plan_features WHERE feature_key = 'advanced_reports'")
existing = cur.fetchall()
print(f"\nExisting advanced_reports features: {len(existing)}")

# Add advanced_reports feature to all active plan versions
now = datetime.now(UTC)
for pv_id, plan_code in plan_versions:
    cur.execute("SELECT id FROM platform_plan_features WHERE plan_version_id = %s AND feature_key = %s", (pv_id, "advanced_reports"))
    if cur.fetchone():
        print(f"  {plan_code}: advanced_reports already exists, skipping")
        continue

    cur.execute(
        """INSERT INTO platform_plan_features (id, plan_version_id, feature_key, enabled, created_at)
           VALUES (%s, %s, %s, %s, %s)""",
        (str(uuid4()), pv_id, "advanced_reports", True, now)
    )
    print(f"  {plan_code}: added advanced_reports feature")

c.commit()

# Verify
cur.execute("""
    SELECT p.code, pf.feature_key, pf.enabled
    FROM platform_plan_features pf
    JOIN platform_plan_versions pv ON pv.id = pf.plan_version_id
    JOIN platform_plans p ON p.id = pv.plan_id
    WHERE pv.is_active = true AND pf.feature_key = 'advanced_reports'
    ORDER BY p.code
""")
print("\nVerified advanced_reports features:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} = {row[2]}")

c.close()
print("\nDone!")
