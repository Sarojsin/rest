import psycopg2
c = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = c.cursor()
cur.execute("select setting, value from restaurant_settings")
for r in cur.fetchall(): print(r)
c.close()