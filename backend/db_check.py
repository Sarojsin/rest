import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Check registrations table columns
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'self_service_registrations' 
    ORDER BY ordinal_position
""")
print("self_service_registrations columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check all registrations
cur.execute("SELECT id, owner_email, plan_code, status, invitation_token_hash FROM self_service_registrations")
print("\nAll registrations:")
for r in cur.fetchall():
    print(f"  ID: {r[0]}, Email: {r[1]}, Plan: {r[2]}, Status: {r[3]}, Token: {r[4][:20] if r[4] else None}...")

# Check platform_one_time_tokens table columns
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'platform_one_time_tokens' 
    ORDER BY ordinal_position
""")
print("\nplatform_one_time_tokens columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check all tokens
cur.execute("SELECT id, email, purpose, restaurant_id, expires_at, used_at FROM platform_one_time_tokens")
print("\nAll one-time tokens:")
for r in cur.fetchall():
    print(f"  ID: {r[0]}, Email: {r[1]}, Purpose: {r[2]}, Restaurant: {r[3]}, Expires: {r[4]}, Used: {r[5]}")

c.close()