"""Remove demo tenant data left by the development seeder.

Keeps the platform realm (platform_* tables, alembic_version) intact so the
superadmin login and plan catalogue survive, while giving the onboarding test a
tenant-free starting point.
"""

import psycopg2

conn = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
conn.autocommit = True
cur = conn.cursor()

cur.execute(
    """
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename NOT LIKE 'platform\\_%'
      AND tablename <> 'alembic_version'
    ORDER BY tablename
    """
)
tables = [row[0] for row in cur.fetchall()]
if tables:
    quoted = ", ".join(f'"{t}"' for t in tables)
    cur.execute(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
    print(f"truncated {len(tables)} tenant/demo tables")
else:
    print("no tenant tables found")

cur.close()
conn.close()
print("tenant cleanup complete")
