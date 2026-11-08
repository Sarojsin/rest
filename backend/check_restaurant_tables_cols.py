import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check restaurant_tables columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurant_tables' ORDER BY ordinal_position")
print("restaurant_tables columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")

cur.close()
c.close()