import psycopg2
c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("select column_name from information_schema.columns where table_name='self_service_registrations'")
print('columns:', [r[0] for r in cur.fetchall()])
cur.execute('select id, restaurant_name, owner_email, status, created_at from self_service_registrations order by created_at desc')
for r in cur.fetchall():
    print(r)
c.close()