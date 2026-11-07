import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check all columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='self_service_registrations'")
print('self_service_registrations columns:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='restaurants'")
print('restaurants columns:', [r[0] for r in cur.fetchall()])

# Check pending registrations for sagardhami84@gmail.com
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status, invitation_token_hash FROM self_service_registrations WHERE owner_email='sagardhami84@gmail.com'")
for r in cur.fetchall():
    print('Registration:', r)

c.close()