"""Remove the temporary E2E test tenant/registrations, keeping the two real tenants."""

import psycopg2

E2E_RESTAURANT_ID = "79552d99-c7b9-4024-9971-6d8f533d6d83"
E2E_EMAILS = ("e2e.owner@example.com", "e2e.reject@example.com")

conn = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
conn.autocommit = False
cur = conn.cursor()

cur.execute(
    """
    SELECT table_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name = 'restaurant_id'
    ORDER BY table_name
    """
)
restaurant_tables = [row[0] for row in cur.fetchall()]

for table in restaurant_tables:
    cur.execute(f'DELETE FROM "{table}" WHERE restaurant_id = %s', (E2E_RESTAURANT_ID,))
    if cur.rowcount:
        print(f"deleted {cur.rowcount} from {table}")

# restaurant_tables resolves its branch FK against restaurants.id in this schema.
cur.execute('DELETE FROM restaurant_tables WHERE branch_id = %s', (E2E_RESTAURANT_ID,))
if cur.rowcount:
    print(f"deleted {cur.rowcount} from restaurant_tables (branch_id)")

cur.execute(
    "DELETE FROM platform_one_time_tokens WHERE restaurant_id = %s OR email = ANY(%s)",
    (E2E_RESTAURANT_ID, list(E2E_EMAILS)),
)
if cur.rowcount:
    print(f"deleted {cur.rowcount} one-time tokens")

cur.execute(
    "DELETE FROM self_service_registrations WHERE restaurant_id = %s OR owner_email = ANY(%s)",
    (E2E_RESTAURANT_ID, list(E2E_EMAILS)),
)
if cur.rowcount:
    print(f"deleted {cur.rowcount} self-service registrations")

cur.execute("DELETE FROM restaurant_memberships WHERE restaurant_id = %s", (E2E_RESTAURANT_ID,))
if cur.rowcount:
    print(f"deleted {cur.rowcount} memberships")

cur.execute("DELETE FROM users WHERE email = ANY(%s)", (list(E2E_EMAILS),))
if cur.rowcount:
    print(f"deleted {cur.rowcount} users")

cur.execute("DELETE FROM restaurants WHERE id = %s", (E2E_RESTAURANT_ID,))
if cur.rowcount:
    print(f"deleted {cur.rowcount} restaurant row")

conn.commit()
cur.close()
conn.close()
print("E2E cleanup complete")
