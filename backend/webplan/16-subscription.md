# Phase 16 — Subscription & SaaS Management Plan

## Objective
Transform the restaurant management system from a single-restaurant software product into a multi-tenant SaaS platform. This includes tenant onboarding, subscription plans, billing cycles, feature access control, and platform-level administration.

## Scope
### Implemented (Foundation)
- Database multi-tenancy foundation: `restaurant_id` on all data tables, `branch_id` for per-restaurant branching
- Tenant isolation via `x-tenant-id` header in API requests
- 73/73 isolation tests passing with per-restaurant data isolation
- `RestaurantMembership` model linking users to restaurants with roles
- Basic user onboarding flow exists
- Phase 9 migration: schema cleaned of legacy `restaurant_id` columns, consolidated to `branch_id`

### New / Planned

1. **Restaurant Registration & Tenant Onboarding**
   - Self-service: new restaurant signs up via web form
  _Onboarding flow_: restaurant details, timezone, currency, initial setup wizard
   - Admin-created: owner creates restaurant account from platform dashboard
   - Verification: email verification, on-site verification (optional)
   - Initial configuration: opening hours, default currency, tax rate, service charge %
   - Welcome setup: import existing data, configure menu items, set up first branch

2. **Subscription Plans**
   - Plan tiers: Free trial, Starter, Professional, Enterprise (or custom names)
   - Pricing: monthly and yearly options (yearly = 2 months free discount)
   - Trial period: 14/30 days free trial before paid plan
   - Plan features matrix: list of features enabled/disabled per tier
   - Plan upgrade/downgrade flow: prorated billing or next-cycle change
   - Plan cancellation: retain access until end of billing period, then read-only or data lock

3. **Feature Access Control**
   - Per-plan feature gating: which modules/restaurants/employees/branches are accessible
   - Feature flag system: `restaurant_settings.plan_tier` gates API routes and UI elements
   - Example feature access:
     - Free: QR menu ordering, basic dashboard (revenue only)
     - Starter: + inventory (limited ingredients), + employee (2 employees), + basic reports
     - Professional: + full inventory, + all employees, + advanced reports, + SMS notifications
     - Enterprise: + multi-branch, + dedicated manager per branch, + priority support, API access
   - Grace period: if plan expires, read-only mode; data retained, no new data can be created

4. **Billing & Subscription Management**
   - Monthly/yearly recurring billing via payment provider (Stripe, eSewa, or manual invoicing)
   - Invoice generation per restaurant per cycle
   - Payment method on file: card, bank transfer details, eSewa account
   - Failed payment handling: grace period (7 days), then suspend restaurant access
   - Subscription renewal: automatic on successful payment; manual renewal link if failed
   - Proration: upgrade mid-cycle charges difference; downgrade credits next cycle

5. **Plan-Based Limits**
   - Branch limits: Free=1 branch, Starter=2 branches, Professional=5 branches, Enterprise=unlimited
   - Employee limits: Free=1 employee, Starter=3, Professional=10, Enterprise=unlimited
   - Ingredient/Item limits: Free=20 menu items, Starter=100, Professional=500, Enterprise=unlimited
   - Order limits: Free=50 orders/month, Starter=500, Professional=5000, Enterprise=unlimited
   - Storage limits: export data size, backup retention period
   - Warning thresholds: 80% of limit reached, alert sent to owner

6. **Usage Tracking & Metering**
   - Track: orders per month, customers, ingredients, employees, API calls, storage used
   - Real-time meter in dashboard: "You've used 240/500 orders this month"
   - Automatic limit enforcement: new orders blocked when limit exceeded (configurable: hard block or soft warning)
   - Usage reset: per monthly anniversary or calendar month (configurable per restaurant)
   - Usage history: view past months' consumption

7. **Plan Upgrade/Downgrade**
   - Initiate upgrade from dashboard: select new plan, confirm prorated charge
   - Downgrade: select new plan, effective at next billing cycle (or immediate with credit)
   - Feature access updates instantly on plan change (or on next API call)
   - Downgrade warning: "You will lose access to X, Y, Z features; data retained but read-only"
   - Migration path: data export before downgrade if data exceeds new plan limits

8. **SaaS Platform Administration**
   - View all restaurants under platform account (if platform serves multiple restaurants)
   - Bulk actions: enable/disable restaurants, export all data, enforce plan changes
   - Sub-agent/agency model: marketing agencies manage multiple restaurant clients
   - Platform support ticket dashboard linked to restaurant IDs
   - Versioning: platform version vs restaurant plan version

9. **Trial to Paid Conversion**
   - Trial dashboard: shows feature access, "Upgrade to Pro" call-to-action
   - Data preservation: trial data retained when upgrading (orders, customers, settings)
   - Import guide: from spreadsheet or competitor software (optional wizard)
   - Kickstart call/onboarding session for Enterprise plans

## Technical Design

### New Models (to be created)
- `Plan` — name (unique), description, price_monthly, price_yearly (nullable for free), trial_days (nullable), is_active, sort_order
- `PlanFeature` — plan_id, feature_name (unique within plan), is_enabled, description, config_json (for feature-specific settings)
- `Subscription` — restaurant_id, plan_id, status (TRIAL, ACTIVE, PAST_DUE, CANCELLED, EXPIRED), billing_cycle (MONTHLY, YEARLY), trial_ends_at, current_period_start, current_period_end, cancel_at_period_end, cancelled_at, payment_provider, provider_subscription_id, payment_method_id, notes
- `UsageMeter` — restaurant_id, date (or month), orders_count, customer_count, ingredient_count, employee_count, storage_bytes, updated_at
- `PaymentTransaction` — subscription_id, amount, provider_txn_id, status (SUCCEEDED, FAILED, PENDING, REFUNDED), payment_method, description, created_at
- `PlanChange` — subscription_id, old_plan_id, new_plan_id, change_type (UPGRADE, DOWNGRADE), prorated_amount, status (PENDING, COMPLETED, FAILED), started_at, completed_at, effective_at, notes

### Existing Models to Extend
- `Restaurant` — add: `plan_id` (FK to Plan, nullable for trial), `status` (TRIAL, ACTIVE, SUSPENDED, CANCELLED), `trial_ends_at`, `trial_used_days`
- `RestaurantSettings` — add: `plan_tier` (enum: FREE, STARTER, PRO, ENT), `feature_gating_json` (which features enabled per plan), `usage_limits_json` (branch_limit, employee_limit, item_limit, order_limit), `billing_cycle`, `payment_processor`, `grace_period_days`
- `User` — optional: `subscription_view_access` (can view across all restaurants in platform)

### API Endpoints (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/plans` | List all available plans |
| `GET /api/v1/subscription` | Get current restaurant subscription details |
| `PATCH /api/v1/subscription` | Update subscription (upgrade/downgrade, cancel) |
| `POST /api/v1/subscription/preview` | Preview plan change: what changes, when effective, prorated amount |
| `GET /api/v1/usage` | Current usage vs limits |
| `GET /api/v1/usage/history` | Historical usage per month |
| `POST /api/v1/usage/reset` | Manually reset usage meter (admin) |
| `GET /api/v1/invoices` | List invoices for restaurant |
| `GET /api/v1/invoice/{id}` | Get invoice PDF or detail |
| `POST /api/v1/payment-method` | Add/update payment method |
| `GET /api/v1/platform/restaurants` | List all restaurants under platform (Agency view) |

### Schemas (new or extended)
- `PlanOut` — id, name, price_monthly, price_yearly, trial_days, features_summary, is_active
- `PlanIn` — name, description, price_monthly, price_yearly, trial_days, features (list of feature names/configs)
- `SubscriptionOut` — plan_name, status, billing_cycle, trial_ends_at, current_period_start/end, cancel_at_period_end, payment_method_last4, provider_txn_id
- `UsageOut` — period, orders_count, customer_count, ingredient_count, employee_count, storage_bytes, limit_{orders,customer,ingredient,employee}, percent_used
- `PaymentTransactionOut` — amount, provider_txn_id, status, created_at, description

### Integration Points
- **Orders**: Subscription status gates order creation/features (Free plan: 50 orders/month hard limit)
- **Customers/Loyalty**: Feature access per plan tier
- **Inventory**: Item limits per plan; ingredient tracking enabled/disabled
- **Employees**: Employee limits per plan; plan gates role creation
- **Dashboard**: Plan tier displayed; usage meter; upgrade CTA
- **Billing**: Payment provider integration (Stripe checkout URLs, eSewa callback URLs)
- **Audit**: All plan changes, subscription updates, usage resets audited
- **Outbox**: Subscription events (trial started, plan changed, payment failed, subscription cancelled)

### Configuration
- Plan list is platform-configured (not hard-coded); admin can add/edit plans via UI
- Feature gating: JSON boolean map per plan, or feature name list
- Grace period: days after expiry before data lock/suspension (default 7)
- Usage reset: per month anniversary (default) or calendar month
- Trial auto-convert: enabled/disabled; if disabled, trial must manually upgrade before data lock
- Proration method: "create_prorations" (Stripe-style) or "next_cycle" (charge full new plan at next anniversary)

## Migration / Rollout Plan
- **Phase 1**: Plan model, Subscription model, basic TRIAL → ACTIVE flow, Restaurant.plan_id + status
- **Phase 2**: Feature gating (per-plan API route guards), usage meters, basic limits (branch/employee count)
- **Phase 3**: Billing integration (payment provider checkout URLs, webhook handling), invoices, payment methods
- **Phase 4**: Plan upgrade/downgrade flow, prorated billing, downgrade warnings, customer self-service
- **Phase 5**: Platform administration (multi-restaurant view), agency model, Enterprise features

Rollback at any phase: remove new tables/columns, revert plan gating, revert Restaurant.plan_id, reset trial states, keep existing restaurant data accessible.

## Acceptance Criteria
- [ ] Restaurant can start a FREE trial (no credit card required)
- [ ] Trial ends and restaurant is prompted to select a paid plan
- [ ] Plan features are gated: Free plan sees only Free features; Pro plan sees all + extras
- [ ] Usage limits enforced: new orders blocked when monthly limit exceeded (soft warning first)
- [ ] Plan upgrade/downgrade works with prorated billing or next-cycle effective date
- [ ] Usage meter shows real-time consumption vs limits
- [ ] Failed payment grace period: 7 days before access suspension
- [ ] Subscription cancellation: access continues until end of billing period
- [ ] All plan/subscription actions audited
- [ ] Existing 73 isolation tests continue to pass (new `plan_id` + `status` columns don't break RLS)
- [ ] 100% of new unit tests pass

## Open Questions / Dependent Work
- Payment provider: Stripe (global, card-based) vs eSewa (local, QR-based) vs manual invoicing?
- Should Free plan have a "made visible" badge or "Powered by [Platform]" requirement?
- How to handle annual vs monthly billing preference per restaurant?
- Proration method detail: should downgrade credits apply immediately or at next cycle?
- What defines a "month" for usage metering: calendar month or anniversary from trial start?
- How to communicate plan changes to restaurant owners (in-app notification, email, both)?
- Platform vs per-restaurant pricing: is the platform fee separate from restaurant plan?

## Phase Order Relative to Other Work
- **Before**: Multi-branch (plan limits include branch counts), Billing (subscription billing feeds into POS billing), Employee (plan limits employee counts), Inventory (plan limits ingredient/menu item counts)
- **After**: Multi-branch (plan enables/disables branch creation), Billing (subscription billing is the foundation for restaurant POS billing), Employee (plan controls employee creation), Inventory (plan controls menu item count)
- **Parallel potential**: All phases — subscription is the horizontal layer that gates all other modules

## Summary Checklist: SaaS Readiness
- [ ] Plan definitions created and configured in DB
- [ ] Restaurant model extended with `plan_id`, `status`, `trial_ends_at`
- [ ] Feature gating middleware implemented (per-plan API guards)
- [ ] Usage meters tracking key metrics
- [ ] Payment provider integration (checkout URLs + webhooks)
- [ ] Self-service upgrade/downgrade flow
- [ ] Grace period and suspension logic
- [ ] Platform administration UI elements
- [ ] Migration script for existing restaurants (assign default plan)