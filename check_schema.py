import psycopg2
conn = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position")
cols = [c[0] for c in cur.fetchall()]
print('users columns:', cols)
cur.close()
conn.close()