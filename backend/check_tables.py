import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'restaurant_tables' 
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()