import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
# Check users table - look for platform admin or superadmin
cur.execute("SELECT id, email, display_name, status FROM users WHERE email LIKE '%harbor%' OR email LIKE '%platform%' OR status = 'SUPERADMIN'")
print('Users with harbor/platform/superadmin:')
for r in cur.fetchall():
    print('  User:', r)

# Check all users
cur.execute("SELECT id, email, display_name, status FROM users")
print('\nAll users:')
for r in cur.fetchall():
    print('  User:', r)

c.close()