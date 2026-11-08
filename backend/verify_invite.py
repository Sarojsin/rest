import psycopg2
c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check invitation tokens
cur.execute("SELECT id, token_hash, purpose, email, restaurant_id, expires_at, created_at FROM platform_one_time_tokens WHERE purpose = 'OWNER_INVITE' ORDER BY created_at DESC LIMIT 5")
tokens = cur.fetchall()
print(f'Invitation tokens:')
for t in tokens:
    print(f'  id={t[0]}, hash={t[1][:30]}..., purpose={t[2]}, email={t[3]}, restaurant_id={t[4]}, expires={t[5]}, created={t[6]}')

# Check registrations
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status, restaurant_id FROM self_service_registrations ORDER BY created_at DESC LIMIT 5")
regs = cur.fetchall()
print(f'\nRegistrations:')
for r in regs:
    print(f'  id={r[0]}, name={r[1]}, email={r[2]}, plan={r[3]}, status={r[4]}, restaurant_id={r[5]}')

# Check users
cur.execute("SELECT id, email, display_name, status FROM users WHERE email = 'sagardhami84@gmail.com'")
users = cur.fetchall()
print(f'\nUsers with sagardhami84@gmail.com:')
for u in users:
    print(f'  id={u[0]}, email={u[1]}, display_name={u[2]}, status={u[3]}')

cur.close()
c.close()