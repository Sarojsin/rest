import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# Test 1: Try SET LOCAL with a made-up parameter
try:
    cur.execute("SET LOCAL app.branch_id = 'test-uuid'")
    print("SET LOCAL succeeded")
    
    cur.execute("SELECT current_setting('app.branch_id')")
    row = cur.fetchone()
    print(f"current_setting: {row}")
except Exception as e:
    print(f"SET LOCAL failed: {e}")

# Test 2: Try SET (not LOCAL)
try:
    cur.execute("SET app.branch_id = 'test-uuid'")
    print("SET succeeded")
    
    cur.execute("SELECT current_setting('app.branch_id')")
    row = cur.fetchone()
    print(f"current_setting: {row}")
except Exception as e:
    print(f"SET failed: {e}")

# Test 3: Just try SHOW
try:
    cur.execute("SHOW app.branch_id")
    print("SHOW succeeded")
except Exception as e:
    print(f"SHOW failed: {e}")

conn.rollback()
cur.close()
conn.close()
print("\nTest complete.")