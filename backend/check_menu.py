import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check menu items for this restaurant
cur.execute("SELECT id, name, slug, price_minor FROM menu_items WHERE restaurant_id = %s", ('30cbcd0c-0b03-42a5-982a-f59f3ac5a82d',))
items = cur.fetchall()
print(f"Menu items ({len(items)}):")
for i in items:
    print(f"  {i[1]} ({i[2]}) - ₹{i[3]/100}")

cur.close()
c.close()