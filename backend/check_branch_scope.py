import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("""
    SELECT rm.id, u.email, rm.role, b.name, b.code
    FROM restaurant_membership_branch rmb
    JOIN restaurant_memberships rm ON rm.id = rmb.membership_id
    JOIN users u ON u.id = rm.user_id
    JOIN branches b ON b.id = rmb.branch_id
    WHERE u.email LIKE 'bahadhami14+%'
    ORDER BY u.email, b.name
""")
print("Branch scope rows:")
for row in cur.fetchall():
    print("  ", row)
c.close()
