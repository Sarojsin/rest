-- Create platform_plan_versions table
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
);

-- Insert 4 active plan versions (adjust plan_id values to match your plans table)
INSERT INTO platform_plan_versions 
  (id, plan_id, version, status, price_annual_minor, price_monthly_minor, trial_days, entitlements)
VALUES
  (gen_random_uuid(), 'basic-plan-uuid', 1, 'ACTIVE', 29000, 2900, 14, 
   '{"branches":{"limit":1},"staff_users":{"limit":5},"orders_per_month":{"limit":1000}}'),
  (gen_random_uuid(), 'professional-plan-uuid', 1, 'ACTIVE', 79000, 7900, 14, 
   '{"branches":{"limit":5},"staff_users":{"limit":25},"orders_per_month":{"limit":10000}}'),
  (gen_random_uuid(), 'enterprise-plan-uuid', 1, 'ACTIVE', 199000, 19900, 14, 
   '{"branches":{"limit":null},"staff_users":{"limit":null},"orders_per_month":{"limit":null}}'),
  (gen_random_uuid(), 'trial-plan-uuid', 1, 'ACTIVE', 0, 0, 14, 
   '{"branches":{"limit":1},"staff_users":{"limit":3},"orders_per_month":{"limit":200}}');

-- Create tenants table if not exists
CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  slug VARCHAR(80) UNIQUE NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
  plan_code VARCHAR(80),
  timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
  currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);