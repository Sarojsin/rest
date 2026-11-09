import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'platform_one_time_tokens'
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(row)
c.close()
