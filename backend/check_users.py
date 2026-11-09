import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")
print('users columns:')
for r in cur.fetchall():
    print(f'  {r[0]}')

cur.execute('SELECT * FROM users')
print('\\nUsers:')
for r in cur.fetchall():
    print(r)

c.close()