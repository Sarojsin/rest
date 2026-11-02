import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

# First, let's add the columns again
conn = psycopg.connect(URL)
cur = conn.cursor()

cols_to_add = [
    ("restaurant_tables", "tenant_id UUID"),
    ("restaurant_tables", "permission_version INT DEFAULT 1"),
    ("orders", "tenant_id UUID"),
    ("orders", "permission_version INT DEFAULT 1"),
    ("bills", "tenant_id UUID"),
    ("bills", "permission_version INT DEFAULT 1"),
    ("payments", "tenant_id UUID"),
    ("payments", "permission_version INT DEFAULT 1"),
    ("dining_sessions", "tenant_id UUID"),
    ("dining_sessions", "permission_version INT DEFAULT 1"),
]

for table, col in cols_to_add:
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col};")
        print(f"Added {col} to {table}")
    except Exception as e:
        print(f"skip {table}.{col} (already exists or error): {e}")

conn.commit()
cur.close()
conn.close()

# Now verify
conn = psycopg.connect(URL)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='restaurant_tables' ORDER BY ordinal_position")
print("restaurant_tables:", [x[0] for x in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='orders' ORDER BY ordinal_position")
print("orders:", [x[0] for x in cur.fetchall()])

cur.close()
conn.close()