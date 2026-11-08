import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check foreign key constraints on restaurant_tables
cur.execute("""
    SELECT con.conname, pg_get_constraintdef(con.oid)
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'restaurant_tables'
    AND con.contype = 'f'
""")
print("FK constraints on restaurant_tables:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print()

# Check branches table structure and data
cur.execute("SELECT id, restaurant_id, name, code FROM branches")
branches = cur.fetchall()
print(f"\nAll branches ({len(branches)}):")
for b in branches:
    print(f"  id={b[0]}, restaurant_id={b[1]}, name={b[2]}, code={b[3]}")

cur.close()
c.close()