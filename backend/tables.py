import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
print('Tables:')
for r in cur.fetchall():
    print(f'  {r[0]}')

c.close()