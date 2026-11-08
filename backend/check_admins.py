import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check platform_admins table structure
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'platform_admins' ORDER BY ordinal_position")
print("platform_admins columns:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Check existing platform admins
cur.execute("SELECT id, email, display_name, role, status FROM platform_admins ORDER BY email")
print("\nExisting platform admins:")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}")

cur.close()
c.close()