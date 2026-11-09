import hashlib, psycopg2
from app.core.security import hash_password

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

# Activate main.waiter user and membership directly
cur.execute("""
    UPDATE users
       SET status = 'ACTIVE',
           password_hash = %s,
           updated_at = NOW()
     WHERE email = 'bahadhami14+main.waiter@gmail.com'
""", (hash_password("Staff@#12345"),))
print("users updated:", cur.rowcount)

cur.execute("""
    UPDATE restaurant_memberships
       SET status = 'ACTIVE',
           updated_at = NOW()
     WHERE user_id = (SELECT id FROM users WHERE email = 'bahadhami14+main.waiter@gmail.com')
""")
print("memberships updated:", cur.rowcount)

c.commit()
c.close()
print("main.waiter activated directly")
