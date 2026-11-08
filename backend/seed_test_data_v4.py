import psycopg2
import uuid
from datetime import UTC, datetime

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

cur.execute("""
    SELECT r.id, r.name, r.slug, u.id as user_id, u.email
    FROM restaurants r
    JOIN restaurant_memberships rm ON r.id = rm.restaurant_id
    JOIN users u ON u.id = rm.user_id
    WHERE u.email = %s AND rm.role = 'owner'
""", ('sagardhami84@gmail.com',))
result = cur.fetchone()
if not result:
    print("No restaurant found for sagardhami84@gmail.com")
    c.close()
    exit(1)

restaurant_id = result[0]
restaurant_name = result[1]
restaurant_slug = result[2]
print(f"Restaurant: {restaurant_name} ({restaurant_slug}) - ID: {restaurant_id}")

cur.execute("SELECT id, name FROM branches WHERE restaurant_id = %s", (restaurant_id,))
existing_branches = cur.fetchall()
if existing_branches:
    branch_id = existing_branches[0][0]
    print(f"Using existing branch: {existing_branches[0][1]} ({branch_id})")
else:
    branch_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO branches (id, restaurant_id, name, code, address, phone, timezone, currency_code, is_active, settings_json, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, '{}', %s, %s)
        RETURNING id
    """, (branch_id, restaurant_id, 'Main Branch', 'main', '123 Main Street', '+977-1-1234567', 'UTC', 'USD', datetime.now(UTC), datetime.now(UTC)))
    branch_id = cur.fetchone()[0]
    print(f"Created branch: Main Branch ({branch_id})")

cur.execute("SELECT table_code FROM restaurant_tables WHERE branch_id = %s", (restaurant_id,))
existing_tables = cur.fetchall()
existing_table_codes = {t[0] for t in existing_tables}
print(f"\nExisting tables ({len(existing_tables)}): {[t[0] for t in existing_tables]}")

for i in range(1, 11):
    table_number = f'S{i}'
    if table_number in existing_table_codes:
        print(f"  Table {i} already exists, skipping")
        continue
    table_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO restaurant_tables (id, branch_id, table_code, display_name, seating_capacity, status, sort_order, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, 'available', %s, %s, %s)
        RETURNING id
    """, (table_id, restaurant_id, table_number, f'Table {i}', min(4 + i % 4, 8), i, datetime.now(UTC), datetime.now(UTC)))
    print(f"Created table: T{i} (capacity: {min(4 + i % 4, 8)})")

c.commit()

cur.execute("SELECT COUNT(*) FROM menu_items WHERE restaurant_id = %s", (restaurant_id,))
menu_count = cur.fetchone()[0]
print(f"\nMenu items: {menu_count}")

if menu_count == 0:
    categories = []
    for cat_name, cat_slug in [('Starters', 'starters'), ('Main Course', 'main-course'), ('Desserts', 'desserts'), ('Beverages', 'beverages')]:
        cat_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO menu_categories (id, restaurant_id, name, description, display_order, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, true, %s, %s)
            RETURNING id
        """, (cat_id, restaurant_id, cat_name, f'{cat_name} dishes', len(categories)+1, datetime.now(UTC), datetime.now(UTC)))
        categories.append((cat_id, cat_name))
        print(f"Created category: {cat_name}")

    menu_items_data = [
        ('Starters', 'Garlic Bread', 'Fresh garlic bread with herbs', 299),
        ('Starters', 'Chicken Wings', 'Spicy chicken wings with dip', 599),
        ('Main Course', 'Margherita Pizza', 'Classic margherita pizza', 899),
        ('Main Course', 'Chicken Burger', 'Grilled chicken burger with fries', 699),
        ('Main Course', 'Veggie Burger', 'Veggie patty burger with fries', 599),
        ('Desserts', 'Chocolate Cake', 'Rich chocolate cake', 399),
        ('Desserts', 'Ice Cream', 'Vanilla ice cream scoop', 199),
        ('Beverages', 'Coca Cola', 'Cold cola drink', 149),
        ('Beverages', 'Fresh Lemonade', 'Fresh homemade lemonade', 249),
    ]
    for cat_name, item_name, desc, price in menu_items_data:
        cat_id = next(c[0] for c in categories if c[1] == cat_name)
        item_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO menu_items (id, restaurant_id, category_id, name, description, current_price_minor, currency_code, status, display_order, image_emoji, image_path, model_path, ingredients_text, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            str(uuid.uuid4()),       # id
            restaurant_id,           # restaurant_id
            cat_id,                  # category_id
            item_name,               # name
            desc,                    # description
            price,                   # current_price_minor
            'USD',                   # currency_code
            'active',                # status
            i,                       # display_order
            '',                      # image_emoji
            '',                      # image_path
            '',                      # model_path
            '',                      # ingredients_text
            datetime.now(UTC),       # created_at
            datetime.now(UTC)        # updated_at
        ))
        menu_items.append((item_id, item_name))
        print(f"Created menu item: {item_name} (₹{price})")
    
    c.commit()

c.commit()
c.close()

print(f"\n{'='*60}")
print("SEED DATA COMPLETE")
print("=" * 60)
print(f"Restaurant: {restaurant_name}")
print(f"Branch: Main Branch ({branch_id})")
cur.execute("SELECT COUNT(*) FROM restaurant_tables WHERE branch_id = %s", (restaurant_id,))
total_tables = cur.fetchone()[0]
print(f"Tables: {total_tables}")
cur.execute("SELECT COUNT(*) FROM menu_items WHERE restaurant_id = %s", (restaurant_id,))
total_menu = cur.fetchone()[0]
print(f"Menu items: {total_menu}")
print(f"\nTest user: sagardhami84@gmail.com / TestPass123!")
print(f"Invitation URL: http://192.168.1.5:5173/auth/invitations/<token>")