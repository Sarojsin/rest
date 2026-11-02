import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

tables = ["orders", "bills", "payments", "dining_sessions"]

for table in tables:
    try:
        cur.execute("ALTER TABLE " + table + " ADD COLUMN branch_id UUID")
        # Set branch_id = restaurant_id for existing rows
        cur.execute("UPDATE " + table + " SET branch_id = restaurant_id WHERE branch_id IS NULL")
        print(f"Added branch_id to {table} and backfilled")
    except Exception as e:
        print(f"  note on {table}: {e} (may already exist)")

conn.commit()
cur.close()
conn.close()
print("Missing branch_id columns added!")