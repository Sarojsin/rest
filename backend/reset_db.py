"""Drop and recreate the public schema for a clean end-to-end test run."""

import psycopg2

conn = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
conn.autocommit = True
cur = conn.cursor()

cur.execute(
    """
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = current_database() AND pid <> pg_backend_pid()
    """
)
cur.execute("DROP SCHEMA public CASCADE")
cur.execute("CREATE SCHEMA public")
cur.execute("GRANT ALL ON SCHEMA public TO postgres")
cur.execute("GRANT ALL ON SCHEMA public TO public")
cur.close()
conn.close()
print("public schema reset complete")
