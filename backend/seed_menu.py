import psycopg2
from uuid import uuid4
from datetime import UTC, datetime

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()

# Get ass restaurant id
cur.execute("SELECT id FROM restaurants WHERE slug = %s", ("ass",))
rest_id = cur.fetchone()[0]
print("Restaurant ass id: %s" % rest_id)

# Create categories
categories = [
    ("Starters", 1, "PUBLISHED"),
    ("Main Course", 2, "PUBLISHED"),
    ("Beverages", 3, "PUBLISHED"),
    ("Desserts", 4, "PUBLISHED"),
]

cat_ids = []
for name, order, status in categories:
    cat_id = str(uuid4())
    now = datetime.now(UTC)
    cur.execute(
        """INSERT INTO menu_categories (id, restaurant_id, name, description, status, display_order, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (cat_id, rest_id, name, "Delicious " + name.lower(), status, order, now, now)
    )
    cat_ids.append(cat_id)
    print("Created category: %s (id=%s)" % (name, cat_id))

# Create items
items = [
    ("Starters", "Garlic Bread", "Freshly baked garlic bread", 250, "PUBLISHED", "🍞"),
    ("Starters", "Caesar Salad", "Crisp romaine with parmesan", 350, "PUBLISHED", "🥗"),
    ("Main Course", "Margherita Pizza", "Tomato, mozzarella, basil", 650, "PUBLISHED", "🍕"),
    ("Main Course", "Grilled Chicken", "Herb-marinated grilled chicken", 850, "PUBLISHED", "🍗"),
    ("Main Course", "Paneer Tikka", "Indian cottage cheese grilled", 550, "PUBLISHED", "🧀"),
    ("Beverages", "Fresh Lime Soda", "Refreshing lime soda", 150, "PUBLISHED", "🥤"),
    ("Beverages", "Masala Chai", "Spiced Indian tea", 80, "PUBLISHED", "☕"),
    ("Desserts", "Gulab Jamun", "Sweet milk dumplings in syrup", 180, "PUBLISHED", "🍮"),
]

item_ids = []
for cat_name, name, desc, price, status, emoji in items:
    cat_id = None
    for cname, cid in zip(["Starters", "Main Course", "Beverages", "Desserts"], cat_ids):
        if cname == cat_name:
            cat_id = cid
            break
    
    item_id = str(uuid4())
    now = datetime.now(UTC)
    cur.execute(
        """INSERT INTO menu_items (id, restaurant_id, category_id, name, description, current_price_minor, currency_code, status, display_order, image_emoji, image_path, model_path, ingredients_text, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (item_id, rest_id, cat_id, name, desc, price, "NPR", status, len(item_ids) + 1, emoji, "", "", "", now, now)
    )
    item_ids.append(item_id)
    print("Created item: %s (price=%s %s)" % (name, price, "NPR"))

c.commit()
c.close()
print("\nDone! Created %d categories and %d items." % (len(cat_ids), len(item_ids)))
