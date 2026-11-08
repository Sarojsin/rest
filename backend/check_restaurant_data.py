import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Find the restaurant owned by sagardhami84@gmail.com
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
print(f"Found restaurant: {restaurant_name} ({restaurant_slug}) - ID: {restaurant_id}")

# Check branches
cur.execute("SELECT id, name, code FROM branches WHERE restaurant_id = %s", (restaurant_id,))
branches = cur.fetchall()
print(f"\nBranches ({len(branches)}):")
for b in branches:
    print(f"  {b[1]} ({b[2]}) - ID: {b[0]}")

# Check tables for each branch
for b in branches:
    cur.execute("SELECT id, table_code, display_name, seating_capacity, status FROM restaurant_tables WHERE branch_id = %s", (b[0],))
    tables = cur.fetchall()
    print(f"\nTables for branch {b[1]} ({len(tables)}):")
    for t in tables:
        print(f"  {t[1]} ({t[2]}) - capacity: {t[3]}, status: {t[4]}, id: {t[0]}")

# Check menu items
cur.execute("SELECT id, name, description, current_price_minor FROM menu_items WHERE restaurant_id = %s", (restaurant_id,))
items = cur.fetchall()
print(f"\nMenu items ({len(items)}):")
for i in items:
    print(f"  {i[1]} - ₹{i[3]/100:.2f} - {i[2]}")

cur.close()
c.close()