import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check plan versions
cur.execute('SELECT id, plan_id, version, is_active, trial_days FROM platform_plan_versions ORDER BY id')
print('Plan versions:')
for r in cur.fetchall():
    print(f'  ID: {r[0]}, plan_id: {r[1]}, version: {r[2]}, is_active: {r[3]}, trial_days: {r[4]}')

# Check public plans mapping
print('\\nFrom earlier: professional plan has trial_days=20')

c.close()