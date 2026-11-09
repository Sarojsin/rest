import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check restaurants columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurants' ORDER BY ordinal_position")
print('restaurants columns:')
for r in cur.fetchall():
    print(f'  {r[0]}')

# Check restaurant_settings columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurant_settings' ORDER BY ordinal_position")
print('\\nrestaurant_settings columns:')
for r in cur.fetchall():
    print(f'  {r[0]}')

# Check platform_subscriptions columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'platform_subscriptions' ORDER BY ordinal_position")
print('\\nplatform_subscriptions columns:')
for r in cur.fetchall():
    print(f'  {r[0]}')

c.close()