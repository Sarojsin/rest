import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("""
    SELECT u.email, rm.role, rm.status
    FROM restaurant_memberships rm
    JOIN users u ON u.id = rm.user_id
    ORDER BY rm.created_at
""")
for row in cur.fetchall():
    print(row)
c.close()
