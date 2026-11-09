import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check restaurants data
cur.execute('SELECT * FROM restaurants')
print('Restaurants:')
for r in cur.fetchall():
    print(f'  {r}')

# Check restaurant settings
cur.execute('SELECT * FROM restaurant_settings')
print('\\nRestaurant Settings:')
for r in cur.fetchall():
    print(f'  {r}')

# Check platform subscriptions
cur.execute('SELECT * FROM platform_subscriptions')
print('\\nPlatform Subscriptions:')
for r in cur.fetchall():
    print(f'  {r}')

c.close()