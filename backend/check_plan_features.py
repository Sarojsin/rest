import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

# Check plan features table columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='platform_plan_features' ORDER BY ordinal_position")
print("platform_plan_features columns:")
for row in cur.fetchall():
    print("  ", row[0])

# Check plan features for starter plan
cur.execute("""
    SELECT pf.feature_key
    FROM platform_plan_features pf
    JOIN platform_plan_versions pv ON pv.id = pf.plan_version_id
    JOIN platform_plans p ON p.id = pv.plan_id
    WHERE pv.is_active = true AND p.code = %s
    ORDER BY pf.feature_key
""", ("starter",))
rows = cur.fetchall()
print("\nStarter plan features:")
if rows:
    for row in rows:
        print("  ", row[0])
else:
    print("  (none)")

# Check all plan features
cur.execute("""
    SELECT p.code, pf.feature_key
    FROM platform_plan_features pf
    JOIN platform_plan_versions pv ON pv.id = pf.plan_version_id
    JOIN platform_plans p ON p.id = pv.plan_id
    WHERE pv.is_active = true
    ORDER BY p.code, pf.feature_key
""")
print("\nAll plan features:")
current_plan = None
for row in cur.fetchall():
    if row[0] != current_plan:
        current_plan = row[0]
        print(f"  {current_plan}:")
    print(f"    - {row[1]}")

c.close()
