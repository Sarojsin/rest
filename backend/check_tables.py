import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'catalog%' ORDER BY tablename")
for row in cur.fetchall():
    print(row[0])
c.close()
