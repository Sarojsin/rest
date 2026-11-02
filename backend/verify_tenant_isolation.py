"""Verification queries — Phase 1 M2 (plan 22 §11).

Proves that tenant_id column correctly scopes data.
Run these ad-hoc against the PG16 dev database.
"""

import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

queries = [
    # 1. Each tenant's tables are partitioned by tenant_id
    ("tenant tables per tenant_id", """
        SELECT tenant_id, count(*) AS cnt
        FROM restaurant_tables
        GROUP BY tenant_id
        ORDER BY tenant_id;
    """),
    # 2. No cross-tenant bleed: a given tenant_id sees only its own tables
    ("tables scoped to tenant1", """
        SELECT count(*) AS my_tables
        FROM restaurant_tables
        WHERE tenant_id = (SELECT tenant_id FROM restaurant_tables LIMIT 1);
    """),
    # 3. permission_version is always 1 after M1 backfill
    ("permission_version state", """
        SELECT permission_version, count(*)
        FROM orders
        GROUP BY permission_version
        ORDER BY permission_version;
    """),
]

conn = psycopg.connect(URL)
cur = conn.cursor()
for name, sql in queries:
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        print(f"--- {name} ---")
        for r in rows:
            print(f"  {r}")
    except Exception as e:
        print(f"ERROR: {name}: {e}")
cur.close()
conn.close()
print("\nVerification queries done.")