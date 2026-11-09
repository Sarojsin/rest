import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

cur.execute(
    """
    SELECT s.restaurant_id, r.name, p.code, p.name, s.status, s.trial_ends_at
      FROM platform_subscriptions s
      JOIN platform_plans p ON p.id = s.plan_id
      JOIN restaurants r ON r.id = s.restaurant_id
     ORDER BY r.name
    """
)
print("subscriptions:")
for row in cur.fetchall():
    print(" ", row)

cur.execute(
    """
    SELECT p.code, l.limit_key, l.limit_value
      FROM platform_plan_limits l
      JOIN platform_plan_versions v ON v.id = l.plan_version_id
      JOIN platform_plans p ON p.id = v.plan_id
     WHERE v.is_active = true
     ORDER BY p.code, l.limit_key
    """
)
print("\nplan limits:")
for row in cur.fetchall():
    print(" ", row)

cur.execute(
    """
    SELECT r.name, r.id FROM restaurants r WHERE r.slug = 'ass'
    """
)
print("\nass restaurant:", cur.fetchall())

c.close()
