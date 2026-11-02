import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

conn = psycopg.connect(URL, autocommit=True)
for table in ["restaurant_tables", "orders", "bills", "payments", "dining_sessions"]:
    # Set tenant_id = restaurant_id for existing rows
    try:
        conn.execute(f"UPDATE {table} SET tenant_id = restaurant_id WHERE tenant_id IS NULL;")
        print(f"Backfilled tenant_id in {table}")
    except Exception as e:
        print(f"skip {table}: {e}")

# Set permission_version = 1 for all rows
for table in ["restaurant_tables", "orders", "bills", "payments", "dining_sessions"]:
    try:
        conn.execute(f"UPDATE {table} SET permission_version = 1 WHERE permission_version IS NULL;")
        print(f"Set permission_version=1 in {table}")
    except Exception as e:
        print(f"skip {table}: {e}")

conn.close()
print("Backfill done.")