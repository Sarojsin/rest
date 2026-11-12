import psycopg2
c = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = c.cursor()

# Get plan features with plan codes
cur.execute("""
    SELECT p.code, f.feature_key, f.enabled
    FROM platform_plan_features f
    JOIN platform_plan_versions pv ON f.plan_version_id = pv.id
    JOIN platform_plans p ON pv.plan_id = p.id
    ORDER BY p.code, f.feature_key
""")
features = cur.fetchall()
print('All plan features:')
for f in features:
    print(f"  {f[0]:12s} {f[1]:25s} {f[2]}")

print()
# Check specific features for each plan
for plan_code in ['starter', 'professional', 'growth', 'enterprise']:
    cur.execute("""
        SELECT f.feature_key, f.enabled
        FROM platform_plan_features f
        JOIN platform_plan_versions pv ON f.plan_version_id = pv.id
        JOIN platform_plans p ON pv.plan_id = p.id
        WHERE p.code = %s
    """, (plan_code,))
    features = cur.fetchall()
    has_menu = any(f[0] == 'menu_management' for f in features)
    print(f'{plan_code:12s} menu_management={has_menu} | features: {[(f[0], f[1]) for f in features]}')

c.close()