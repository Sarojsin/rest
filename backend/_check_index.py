import psycopg2
c = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = c.cursor()
cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'restaurant_tables'")
indexes = cur.fetchall()
print('Indexes on restaurant_tables:')
for idx in indexes:
    print(f'  {idx[0]}: {idx[1]}')
c.close()