import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'table_qr_codes' ORDER BY ordinal_position")
print("table_qr_codes columns:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
cur.close()
c.close()