import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# First, let's see the current state of plan versions
print("=== Before update ===")
cur.execute("SELECT id, plan_id, version, is_active FROM platform_plan_versions")
for r in cur.fetchall():
    print(f"  id={r[0]}, plan_id={r[1]}, version={r[2]}, is_active={r[3]}")

# Now activate all plan versions
print("\n=== Activating all plan versions ===")
cur.execute("UPDATE platform_plan_versions SET is_active = true")
count = cur.rowcount
print(f"Updated {count} plan versions to is_active = true")

c.commit()

# Verify the update
print("\n=== After update ===")
cur.execute("SELECT id, plan_id, version, is_active FROM platform_plan_versions")
for r in cur.fetchall():
    print(f"  id={r[0]}, plan_id={r[1]}, version={r[2]}, is_active={r[3]}")

c.close()