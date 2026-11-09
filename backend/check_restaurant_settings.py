import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

# Check restaurant columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='restaurants' ORDER BY ordinal_position")
print("restaurants columns:")
for row in cur.fetchall():
    print("  ", row[0])

# Check restaurant
cur.execute("SELECT id, name, slug FROM restaurants WHERE slug = 'ass'")
for row in cur.fetchall():
    print("\nRestaurant:", row)

# Check restaurant_settings table
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='restaurant_settings' ORDER BY ordinal_position")
print("\nrestaurant_settings columns:")
for row in cur.fetchall():
    print("  ", row[0])

cur.execute("SELECT * FROM restaurant_settings WHERE restaurant_id = (SELECT id FROM restaurants WHERE slug = 'ass')")
rows = cur.fetchall()
if rows:
    print("\nrestaurant_settings row:")
    for row in rows:
        print("  ", row)
else:
    print("\nNo restaurant_settings row found for 'ass'")

c.close()
