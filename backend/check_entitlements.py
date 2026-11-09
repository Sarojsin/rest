import json
import psycopg2

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("SELECT code, entitlements FROM platform_plans ORDER BY code")
for code, ent in cur.fetchall():
    print(code, json.dumps(ent, indent=2, sort_keys=True))
c.close()
