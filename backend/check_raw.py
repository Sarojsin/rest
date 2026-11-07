import psycopg2

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()
cur.execute("SELECT id, plan_id, version, is_active FROM platform_plan_versions")
for r in cur.fetchall():
    print(f"  id={r[0]}, plan_id={r[1]}, version={r[2]}, is_active={r[3]}, type_is_active={type(r[3])}")

c.close()