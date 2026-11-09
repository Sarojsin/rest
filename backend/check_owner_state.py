import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

cur.execute(
    "SELECT column_name, data_type, is_nullable, column_default "
    "FROM information_schema.columns WHERE table_name='branches' ORDER BY ordinal_position"
)
print("branches columns:")
for row in cur.fetchall():
    print(" ", row)

cur.execute("SELECT * FROM branches")
cols = [d[0] for d in cur.description]
print("\nbranches rows:")
for row in cur.fetchall():
    print(" ", dict(zip(cols, row)))

cur.execute(
    "SELECT id, restaurant_id, owner_email, status, restaurant_slug, restaurant_name "
    "FROM self_service_registrations ORDER BY created_at"
)
print("\nregistrations:")
for row in cur.fetchall():
    print(" ", row)

cur.execute(
    "SELECT email, purpose, restaurant_id, expires_at, used_at "
    "FROM platform_one_time_tokens ORDER BY created_at"
)
print("\ntokens:")
for row in cur.fetchall():
    print(" ", row)

c.close()
