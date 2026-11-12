import psycopg2
c = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = c.cursor()

# Step 1: Clear all existing plan features
cur.execute("DELETE FROM platform_plan_features")
print("Step 1: Cleared all plan features")

# Step 2: Define canonical features per plan
features = {
    'starter': [
        ('qr_ordering', True),
        ('menu_management', True),
        ('bills_issue', True),
        ('payments_record', True),
        ('kitchen_update', True),
    ],
    'professional': [
        ('qr_ordering', True),
        ('menu_management', True),
        ('inventory', True),
        ('advanced_reports', True),
        ('bills_issue', True),
        ('payments_record', True),
        ('kitchen_update', True),
    ],
    'growth': [
        ('qr_ordering', True),
        ('menu_management', True),
        ('inventory', True),
        ('advanced_reports', True),
        ('loyalty', True),
        ('online_payment', True),
        ('bills_issue', True),
        ('payments_record', True),
        ('kitchen_update', True),
    ],
    'enterprise': [
        ('qr_ordering', True),
        ('menu_management', True),
        ('inventory', True),
        ('advanced_reports', True),
        ('loyalty', True),
        ('online_payment', True),
        ('bills_issue', True),
        ('payments_record', True),
        ('kitchen_update', True),
    ],
}

plan_codes = ['starter', 'professional', 'growth', 'enterprise']
plan_ids = {}
for plan_code in plan_codes:
    cur.execute("SELECT id FROM platform_plans WHERE code = %s", (plan_code,))
    plan_id = cur.fetchone()[0]
    plan_ids[plan_code] = plan_id
    cur.execute("SELECT id FROM platform_plan_versions WHERE plan_id = %s AND is_active = TRUE", (plan_id,))
    version_id = cur.fetchone()[0]
    cur.execute("DELETE FROM platform_plan_features WHERE plan_version_id = %s", (version_id,))
    for feature_key, enabled in features[plan_code]:
        cur.execute(
            "INSERT INTO platform_plan_features (id, plan_version_id, feature_key, enabled, created_at) VALUES (gen_random_uuid(), %s, %s, %s, NOW())",
            (version_id, feature_key, enabled)
        )

print("Step 2: Updated all plan features with canonical keys")

# Step 3: Verify
cur.execute("""
    SELECT p.code, f.feature_key, f.enabled
    FROM platform_plan_features f
    JOIN platform_plan_versions pv ON f.plan_version_id = pv.id
    JOIN platform_plans p ON pv.plan_id = p.id
    ORDER BY p.code, f.feature_key
""")
rows = cur.fetchall()
print("\nStep 3: Verified plan features:")
for r in rows:
    print(f"  {r[0]:12s} {r[1]:25s} {r[2]}")

print("\nmenu_management status:")
for plan_code in plan_codes:
    has_menu = any(f[0] == 'menu_management' and f[2] == True for f in rows if f[0] == plan_code)
    print(f"  {plan_code:12s} menu_management={has_menu}")

c.commit()
c.close()
print("\nDone! Plan features now use canonical keys.")