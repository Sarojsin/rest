import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# Check current policies
cur.execute("SELECT polname FROM pg_policy WHERE polrelid = 'restaurant_tables'::regclass")
for r in cur.fetchall():
    print(f"Existing policy: {r[0]}")

# Create the policy
pol_sql = (
    "CREATE POLICY branch_isolation ON restaurant_tables " +
    "USING (branch_id::text = current_setting('app.branch_id')) " +
    "WITH CHECK (branch_id::text = current_setting('app.branch_id'))"
)
try:
    cur.execute(pol_sql)
    print("Created branch_isolation policy on restaurant_tables")
except Exception as e:
    print(f"Error creating policy: {e}")

conn.close()