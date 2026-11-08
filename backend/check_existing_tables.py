import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT table_code, display_name, seating_capacity, status FROM restaurant_tables ORDER BY table_code")
tables = cur.fetchall()
print(f"Existing tables ({len(tables)}):")
for t in tables:
    print(f"  {t[1]} ({t[0]}) - capacity: {t[2]}, status: {t[3]}")

cur.close()
c.close()