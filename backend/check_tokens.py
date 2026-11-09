import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("""
    SELECT id, email, purpose, expires_at, used_at, created_at
    FROM platform_one_time_tokens
    WHERE purpose = 'STAFF_INVITE'
    ORDER BY created_at DESC
""")
for row in cur.fetchall():
    print(row)
c.close()
