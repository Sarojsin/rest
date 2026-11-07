import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations ORDER BY created_at DESC LIMIT 5")
print("Recent registrations:")
for r in cur.fetchall():
    print(f"  id={r[0]}, name={r[1]}, email={r[2]}, plan={r[3]}, status={r[4]}")

# Check the sagardhami84 one specifically
cur.execute("SELECT id, restaurant_name, owner_email, plan_code, status FROM self_service_registrations WHERE owner_email = 'sagardhami84@gmail.com'")
print("\nsagardhami84@gmail.com registration:")
for r in cur.fetchall():
    print(f"  id={r[0]}, name={r[1]}, email={r[2]}, plan={r[3]}, status={r[4]}")

c.close()