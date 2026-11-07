import psycopg2
c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("select id, restaurant_name, restaurant_slug, owner_email, plan_code, status, created_at from self_service_registrations order by created_at desc")
for r in cur.fetchall():
    print(r)
cur.execute("select id, name, slug, status, created_at from restaurants order by created_at desc")
print('restaurants:')
for r in cur.fetchall():
    print(r)
c.close()
