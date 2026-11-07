import psycopg2
import uuid

conn = psycopg2.connect("postgresql+psycopg2://postgres:tara@localhost:5432/restaurant")
cur = conn.cursor()

# Create platform_plan_versions table
cur.execute("""
CREATE TABLE IF NOT EXISTS platform_plan_versions (
  id UUID PRIMARY KEY,
  plan_id UUID NOT NULL REFERENCES plans(id),
  version INT NOT NULL DEFAULT 1,
  status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
  price_annual_minor INT NOT NULL DEFAULT 0,
  price_monthly_minor INT NOT NULL DEFAULT 0,
  trial_days INT NOT NULL DEFAULT 14,
  entitlements JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
""")
print('platform_plan_versions table created')

# Insert 4 active plan versions
plan_ids = ['basic-plan-uuid', 'professional-plan-uuid', 'enterprise-plan-uuid', 'trial-plan-uuid']
for plan_id in plan_ids:
    entitlements = '{"branches":{"limit":1},"staff_users":{"limit":5},"orders_per_month":{"limit":1000}}'
    if plan_id == 'professional-plan-uuid':
        entitlements = '{"branches":{"limit":5},"staff_users":{"limit":25},"orders_per_month":{"limit":10000}}'
    elif plan_id == 'enterprise-plan-uuid':
        entitlements = '{"branches":{"limit":null},"staff_users":{"limit":null},"orders_per_month":{"limit":null}}'
    elif plan_id == 'trial-plan-uuid':
        entitlements = '{"branches":{"limit":1},"staff_users":{"limit":3},"orders_per_month":{"limit":200}}'
    
    cur.execute("""
INSERT INTO platform_plan_versions 
  (id, plan_id, version, status, price_annual_minor, price_monthly_minor, trial_days, entitlements)
VALUES
  (gen_random_uuid(), %s, 1, 'ACTIVE', 29000, 2900, 14, %s)
""", (plan_id, entitlements))
    print(f'Inserted plan version for {plan_id}')

conn.commit()
cur.close()
conn.close()
print('Database setup complete')