import psycopg2
c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE owner_email = %s", ('sagardhami84@gmail.com',))
reg = cur.fetchone()
print(f'Registration: {reg}')

cur.execute("SELECT id, token_hash, purpose, email, restaurant_id, expires_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' ORDER BY created_at DESC LIMIT 5")
tokens = cur.fetchall()
print(f'\nExisting invitation tokens:')
for t in tokens:
    print(f'  id={t[0]}, hash={t[1][:20]}..., purpose={t[2]}, email={t[3]}, restaurant_id={t[4]}, expires={t[5]}')

cur.close()
c.close()