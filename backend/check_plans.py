import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check plan versions
print("=== Platform Plan Versions ===")
cur.execute("SELECT id, plan_id, version, is_active, effective_from FROM platform_plan_versions ORDER BY plan_id, version")
for r in cur.fetchall():
    print(f"  plan_id={r[0]}, version={r[1]}, is_active={r[2]}, effective_from={r[3]}")

# Check active plans
print("\n=== Active Plans ===")
cur.execute("SELECT id, code, name, is_public, status FROM platform_plans WHERE is_public = true AND status = 'ACTIVE'")
for r in cur.fetchall():
    print(f"  code={r[1]}, name={r[2]}, is_public={r[3]}, status={r[4]}")

# Check the specific registration
print("\n=== Registration with sagardhami84@gmail.com ===")
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE owner_email='sagardhami84@gmail.com'")
for r in cur.fetchall():
    print(f"  id={r[0]}, name={r[1]}, email={r[2]}, plan={r[3]}, status={r[4]}")

    # Check plan for this registration
    plan_code = r[3]
    cur.execute("SELECT id, code, name, is_public, status FROM platform_plans WHERE code = %s AND is_public = true AND status = 'ACTIVE'", (plan_code,))
    plan = cur.fetchone()
    print(f"  Plan in DB: {plan}")

    # Check plan versions
    if plan:
        cur.execute("SELECT id, plan_id, version, is_active FROM platform_plan_versions WHERE plan_id = %s ORDER BY version DESC", (plan[0],))
        versions = cur.fetchall()
        print(f"  Plan versions: {versions}")

c.close()