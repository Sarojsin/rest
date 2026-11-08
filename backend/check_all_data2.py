import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check all branches
cur.execute("SELECT id, restaurant_id, name, code FROM branches")
branches = cur.fetchall()
print(f"All branches ({len(branches)}):")
for b in branches:
    print(f"  id={b[0]}, restaurant_id={b[1]}, name={b[2]}, code={b[3]}")

# Check all tables
cur.execute("SELECT id, branch_id, table_code, display_name FROM restaurant_tables ORDER BY table_code")
tables = cur.fetchall()
print(f"\nAll tables ({len(tables)}):")
for t in tables:
    print(f"  {t[0]} - branch_id={t[1]}, code={t[2]}, name={t[3]}")

# Find which restaurant the tables belong to
if tables:
    branch_id = tables[0][1]
    cur.execute("SELECT name FROM branches WHERE id = %s", (branch_id,))
    branch_result = cur.fetchone()
    if branch_result:
        print(f"\nTables belong to branch: {branch_result[0]} (ID: {branch_id})")
    
    # Find which restaurant this branch belongs to
    cur.execute("SELECT name, slug FROM restaurants WHERE id = %s", (branch_id,))
    rest_result = cur.fetchone()
    if rest_result:
        print(f"Branch belongs to restaurant: {rest_result[0]} ({rest_result[1]})")

cur.close()
c.close()