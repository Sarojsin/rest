import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

conn = psycopg.connect(URL)
cur = conn.cursor()

# Check tenant_id column exists
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='restaurant_tables' AND column_name='tenant_id'")
print("tenant_id in restaurant_tables:", cur.fetchall())

# Check permission_version in orders
cur.execute("SELECT permission_version, count(*) FROM orders GROUP BY permission_version ORDER BY permission_version")
print("permission_version in orders:", cur.fetchall())

cur.close()
conn.close()