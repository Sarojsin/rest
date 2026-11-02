import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# Check policies
cur.execute("SELECT polname, polcmd, polroles FROM pg_policy WHERE polrelid = 'restaurant_tables'::regclass")
for r in cur.fetchall():
    print(f"Policy: {r}")

# Check RLS status
cur.execute("SELECT relname, relisfromrules FROM pg_class WHERE relname = 'restaurant_tables'")
r = cur.fetchone()
print(f"RLS enabled: {r[1]}")

conn.close()