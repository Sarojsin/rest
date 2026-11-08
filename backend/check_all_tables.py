import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("SELECT id, branch_id, table_code, display_name, seating_capacity, status FROM restaurant_tables ORDER BY table_code")
tables = cur.fetchall()
print(f"All tables ({len(tables)}):")
for t in tables:
    print(f"  id={t[0]}, branch_id={t[1]}, code={t[2]}, name={t[3]}, capacity={t[4]}, status={t[5]}")

# Also check branches
cur.execute("SELECT id, restaurant_id, name, code FROM branches")
branches = cur.fetchall()
print(f"\nAll branches ({len(branches)}):")
for b in branches:
    print(f"  id={b[0]}, restaurant_id={b[1]}, name={b[2]}, code={b[3]}")

cur.close()
c.close()