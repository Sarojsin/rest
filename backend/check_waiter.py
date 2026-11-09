import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("""
    SELECT u.email, u.status, rm.role, rm.status, rm.token_version
    FROM restaurant_memberships rm
    JOIN users u ON u.id = rm.user_id
    WHERE u.email LIKE 'bahadhami14+%'
    ORDER BY u.email
""")
for row in cur.fetchall():
    print(row)
c.close()
