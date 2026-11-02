import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

conn = psycopg.connect(URL, autocommit=True)

# Add branch_id column to all 5 tables
tables = ["restaurant_tables", "orders", "bills", "payments", "dining_sessions"]
for table in tables:
    conn.execute(f"ALTER TABLE {table} ADD COLUMN branch_id UUID")
    print(f"Added branch_id to {table}")

conn.commit()
conn.close()
print("branch_id columns added.")