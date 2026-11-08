import psycopg2
c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations ORDER BY created_at DESC")
regs = cur.fetchall()
print(f'All self_service_registrations ({len(regs)}):')
for r in regs:
    print(f'  id={r[0]}, name={r[1]}, email={r[2]}, plan={r[3]}, status={r[4]}')

cur.execute("SELECT id, name, slug, status FROM restaurants ORDER BY created_at DESC")
rests = cur.fetchall()
print(f'\nAll restaurants ({len(rests)}):')
for r in rests:
    print(f'  id={r[0]}, name={r[1]}, slug={r[2]}, status={r[3]}')

cur.execute("SELECT id, email, password_hash, display_name, status FROM users ORDER BY created_at DESC")
users = cur.fetchall()
print(f'\nAll users ({len(users)}):')
for u in users:
    print(f'  id={u[0]}, email={u[1]}, display_name={u[3]}, status={u[4]}')

cur.close()
c.close()