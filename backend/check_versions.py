import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check plan versions more carefully
print("=== All plan versions ===")
cur.execute("""
    SELECT pv.id, pv.plan_id, pv.version, pv.is_active, pv.effective_from, p.code as plan_code 
    FROM platform_plan_versions pv 
    JOIN platform_plans p ON pv.plan_id = p.id 
    ORDER BY pv.plan_id, pv.version DESC
""")
for r in cur.fetchall():
    print(f"  pv_id={r[0]}, plan_id={r[1]}, version={r[2]}, active={r[3]}, eff_from={r[4]}, plan_code={r[5]}")

# Check if any plans have no active versions
print("\n=== Plans with NO active versions ===")
cur.execute("""
    SELECT p.id, p.code, p.name, COUNT(pv.id) as total_versions,
           COUNT(CASE WHEN pv.is_active THEN 1 END) as active_version_count
    FROM platform_plans p LEFT JOIN platform_plan_versions pv ON pv.plan_id = p.id
    GROUP BY p.id, p.code, p.name
    HAVING COUNT(CASE WHEN pv.is_active THEN 1 END) = 0 OR COUNT(pv.id) = 0
""")
for r in cur.fetchall():
    print(f"  plan={r[1]}, total_versions={r[3]}, active_versions={r[4]}")

c.close()