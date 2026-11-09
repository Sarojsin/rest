import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check registrations columns and data
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'self_service_registrations' ORDER BY ordinal_position")
print('self_service_registrations columns:')
for r in cur.fetchall():
    print(f'  {r[0]}')

cur.execute('SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations')
print('\nCurrent registrations:')
for r in cur.fetchall():
    print(f'  {r}')

# Check plan versions
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'platform_plan_versions' ORDER BY ordinal_position")
print('\nplatform_plan_versions columns:')
for r in cur.fetchall():
    print(f'  {r[0]}')

cur.execute('SELECT id, plan_id, version, is_active, trial_days FROM platform_plan_versions')
print('\nCurrent plan versions:')
for r in cur.fetchall():
    print(f'  {r}')

c.close()