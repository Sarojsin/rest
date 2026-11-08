import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check all invitation tokens for sagardhami84@gmail.com
cur.execute("SELECT id, token_hash, purpose, email, restaurant_id, expires_at, used_at, created_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' AND email = %s ORDER BY created_at DESC LIMIT 10", ('sagardhami84@gmail.com',))
tokens = cur.fetchall()
print(f'Invitation tokens ({len(tokens)}):')
for t in tokens:
    print(f'  id={t[0]}, hash={t[1][:30]}..., email={t[3]}, restaurant_id={t[4]}, expires={t[5]}, used_at={t[6]}, created={t[7]}')

# Check user
cur.execute("SELECT id, email, display_name, status FROM users WHERE email = %s", ('sagardhami84@gmail.com',))
user = cur.fetchone()
print(f'\nUser: {user}')

# Check registrations
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status, restaurant_id FROM self_service_registrations WHERE owner_email = %s ORDER BY created_at DESC LIMIT 5", ('sagardhami84@gmail.com',))
regs = cur.fetchall()
print(f'\nRegistrations ({len(regs)}):')
for r in regs:
    print(f'  id={r[0]}, name={r[1]}, email={r[2]}, plan={r[3]}, status={r[4]}, restaurant_id={r[5]}')

cur.close()
c.close()