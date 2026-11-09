import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

cur.execute("SELECT id, name, slug, status FROM restaurants ORDER BY created_at")
print("restaurants:", cur.fetchall())

cur.execute("SELECT email, status FROM users ORDER BY created_at")
print("users:", cur.fetchall())

cur.execute(
    "SELECT email, purpose, restaurant_id, expires_at, used_at "
    "FROM platform_one_time_tokens ORDER BY created_at"
)
print("tokens:", cur.fetchall())

cur.execute(
    "SELECT restaurant_id, status, trial_ends_at, plan_id FROM platform_subscriptions"
)
print("subs:", cur.fetchall())

c.close()
