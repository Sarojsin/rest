import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# Drop all policies on restaurant_tables
cur.execute("""
    DROP POLICY IF EXISTS test_pol ON restaurant_tables;
    DROP POLICY IF EXISTS branch_isolation ON restaurant_tables;
""")
print("Dropped all policies on restaurant_tables")

# Check remaining policies
cur.execute("SELECT polname FROM pg_policy WHERE polrelid = 'restaurant_tables'::regclass")
for r in cur.fetchall():
    print(f"Remaining policy: {r[0]}")

# Disable RLS, recreate policy, re-enable
cur.execute("ALTER TABLE restaurant_tables DISABLE ROW LEVEL SECURITY")
print("Disabled RLS")

cur.execute("""
    CREATE POLICY branch_isolation ON restaurant_tables
    USING (branch_id::text = current_setting('app.branch_id'))
    WITH CHECK (branch_id::text = current_setting('app.branch_id'))
""")
print("Created branch_isolation policy")

cur.execute("ALTER TABLE restaurant_tables ENABLE ROW LEVEL SECURITY")
print("Enabled RLS")

conn.commit()
conn.close()
print("Done.")