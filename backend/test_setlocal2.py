import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=False)
cur = conn.cursor()

# Test: SET LOCAL within a transaction
try:
    cur.execute("BEGIN")
    cur.execute("SET LOCAL app.branch_id = 'test-uuid'")
    cur.execute("SELECT current_setting('app.branch_id')")
    row = cur.fetchone()
    print(f"Within transaction - current_setting: {row}")
    
    cur.execute("SELECT count(*) FROM restaurant_tables")
    row = cur.fetchone()
    print(f"Count within transaction: {row}")
    
    cur.execute("ROLLBACK")
    print("Rolled back")
except Exception as e:
    print(f"Error: {e}")
    try:
        cur.execute("ROLLBACK")
    except:
        pass

# Test: SET without LOCAL (session-level)
try:
    cur.execute("SET app.branch_id = 'test-uuid'")
    cur.execute("SELECT current_setting('app.branch_id')")
    row = cur.fetchone()
    print(f"Session-level - current_setting: {row}")
    
    cur.execute("SELECT count(*) FROM restaurant_tables")
    row = cur.fetchone()
    print(f"Count with session-level SET: {row}")
    
    cur.execute("RESET app.branch_id")
    print("Reset")
except Exception as e:
    print(f"Error: {e}")

conn.close()
print("\nTest complete.")