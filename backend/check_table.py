import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check table structure
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'platform_plan_versions' ORDER BY ordinal_position")
print('Columns:', cur.fetchall())

# Check count
cur.execute('SELECT count(*) FROM platform_plan_versions')
print('Row count:', cur.fetchone())

# Check if table exists
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'platform_plan_versions'
""")
print('Table exists:', cur.fetchone())

c.close()