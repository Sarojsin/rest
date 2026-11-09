import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'platform_plan_versions' ORDER BY ordinal_position")
print('platform_plan_versions columns:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

c.close()