import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# Check for existing policies
cur.execute("""
    SELECT polname, polcmd, polroles, polqual, polwithcheck
    FROM pg_policy
    WHERE polrelid = 'restaurant_tables'::regclass
""")
rows = cur.fetchall()
print("Existing policies on restaurant_tables:")
for r in rows:
    print(f"  {r}")

conn.close()