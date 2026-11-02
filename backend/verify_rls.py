import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"
conn = psycopg.connect(URL, autocommit=True)
cur = conn.cursor()

# Test 1: Without SET LOCAL, count should still be 6 (policy uses current_setting)
cur.execute("SELECT count(*) FROM restaurant_tables")
row = cur.fetchone()
print(f"Count without SET LOCAL: {row}")

# Test 2: With SET LOCAL in a transaction
conn2 = psycopg.connect(URL, autocommit=False)
cur2 = conn2.cursor()
cur2.execute("BEGIN")
cur2.execute("SET LOCAL app.branch_id = 'fe34bdad-2132-4db4-a763-14da29a0eb7f'")
cur2.execute("SELECT count(*) FROM restaurant_tables")
row = cur2.fetchone()
print(f"Count WITH SET LOCAL (matching branch_id): {row}")

cur2.execute("ROLLBACK")
conn2.close()

# Test 3: Without SET LOCAL in a new transaction
conn3 = psycopg.connect(URL, autocommit=False)
cur3 = conn3.cursor()
cur3.execute("BEGIN")
cur3.execute("SELECT count(*) FROM restaurant_tables")
row = cur3.fetchone()
print(f"Count in new tx without SET LOCAL: {row}")

cur3.execute("ROLLBACK")
conn3.close()

print("\nRLS functional test complete.")
conn.close()