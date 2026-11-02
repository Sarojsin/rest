import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# M4: Make branch_id NOT NULL (flag-gated read switch)
tables = ["restaurant_tables", "orders", "bills", "payments", "dining_sessions"]

for table in tables:
    try:
        # First set branch_id = restaurant_id for any NULLs
        conn.execute(f"UPDATE {table} SET branch_id = restaurant_id WHERE branch_id IS NULL")
        # Then make it NOT NULL
        conn.execute(f"ALTER TABLE {table} ALTER COLUMN branch_id SET NOT NULL")
        print(f"Made branch_id NOT NULL in {table}")
    except Exception as e:
        print(f"skip {table}: {e}")

# Create indexes for branch-switch queries
for table in tables:
    try:
        conn.execute(f"CREATE INDEX idx_{table}_branch_id ON {table} (branch_id)")
        print(f"Created index on branch_id for {table}")
    except Exception as e:
        print(f"skip index on {table}: {e}")

conn.commit()
cur.close()
conn.close()
print("M4 constraints done.")