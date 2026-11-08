import psycopg2
from argon2 import PasswordHasher

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT id, email, password_hash FROM users WHERE email = %s", ('sagardhami84@gmail.com',))
user = cur.fetchone()
if user:
    print(f'User: id={user[0]}, email={user[1]}')
    print(f'Password hash: {user[2]}')
    
    # Try to verify the password
    ph = PasswordHasher()
    try:
        result = ph.verify(user[2], 'TestPass123!')
        print(f'Password "TestPass123!" matches: {result}')
    except Exception as e:
        print(f'Password "TestPass123!" does NOT match: {type(e).__name__}: {e}')
    
    # Also try without exclamation
    try:
        result = ph.verify(user[2], 'TestPass123')
        print(f'Password "TestPass123" matches: {result}')
    except Exception as e:
        print(f'Password "TestPass123" does NOT match: {type(e).__name__}: {e}')

cur.close()
c.close()