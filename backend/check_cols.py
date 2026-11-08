import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'menu_categories' ORDER BY ordinal_position")
print("menu_categories columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'menu_items' ORDER BY ordinal_position")
print("menu_items columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")
cur.close()
c.close()