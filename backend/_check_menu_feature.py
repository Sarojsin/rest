import psycopg2
c = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = c.cursor()

cur.execute('SELECT id, code, name FROM platform_plans ORDER BY code')
plans = cur.fetchall()

for plan in plans:
    plan_id = plan[0]
    cur.execute('SELECT id FROM platform_plan_versions WHERE plan_id = %s AND is_active = TRUE', (plan_id,))
    version = cur.fetchone()
    if not version:
        print(f'{plan[1]}: NO ACTIVE VERSION')
        continue
    cur.execute('SELECT feature_key, enabled FROM platform_plan_features WHERE plan_version_id = %s', (version[0],))
    features = cur.fetchall()
    has_menu = any(f[0] == 'menu_management' for f in features)
    print(f'{plan[1]}: menu_management={"YES" if has_menu else "NO"} | features: {[f[0] for f in features]}')

c.close()