import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

# Check menu categories
cur.execute("SELECT id, name, status, display_order, restaurant_id FROM menu_categories ORDER BY name")
rows = cur.fetchall()
print("Menu categories (%d):" % len(rows))
for row in rows:
    print("  %s | %s | %s | order=%s | restaurant=%s" % row)

# Check menu items
cur.execute("SELECT id, name, status, current_price_minor, category_id, restaurant_id FROM menu_items ORDER BY name")
rows = cur.fetchall()
print("\nMenu items (%d):" % len(rows))
for row in rows:
    print("  %s | %s | %s | %s | cat=%s | rest=%s" % row)

c.close()
