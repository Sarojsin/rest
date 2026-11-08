import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check user
cur.execute("SELECT id, email, display_name, status, password_hash FROM users WHERE email = %s", ('sagardhami84@gmail.com',))
user = cur.fetchone()
if user:
    print(f'User: id={user[0]}, email={user[1]}, display_name={user[2]}, status={user[3]}')
    print(f'Password hash exists: {bool(user[4])}')
    print(f'Password hash length: {len(user[4]) if user[4] else 0}')
else:
    print('User does not exist')

cur.close()
c.close()