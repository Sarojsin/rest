# Phase 12 — Multi-Branch Management Plan

## Objective
Enable a restaurant business to operate one or multiple branches under a single account, with per-branch isolation of menus, tables, employees, and inventory, while providing a centralized owner dashboard for comparison and management.

## Scope
### Implemented (Foundation)
- `restaurants` table with basic restaurant info
- `branch_id` on `RestaurantTable` — FK to `restaurants.id` (not self-referential; each restaurant has many branches)
- `restaurant_id` on `Order`, `OrderItem`, `OrderRating`, `TableQrCode`, `DiningSession` — FK to `restaurants.id`
- Tenant isolation via `x-tenant-id` header + `branch_id` on `RestaurantTable`
- 73/73 isolation tests passing with per-restaurant data isolation
- `RestaurantMembership` — links users to restaurants with roles
- Phase 9 migration: `restaurant_id` dropped from `order_items`, `order_ratings`, `restaurant_tables`; consolidated to `branch_id`

### New / Planned

1. **Branch Creation & Configuration**
   - Owner/manager can create new branches under their account
   - Branch name, address, phone, timezone, currency (if multi-currency)
   - Branch-specific settings: opening hours, dine-in/takeaway enabled, service charge %, tax rate
   - Branch logo/branding customization

2. **Per-Branch Menus & Pricing**
   - Each branch has its own menu configuration
   - Same MenuItem can exist across branches with different prices
   - Branch-level enable/disable of dishes (some items only at certain locations)
   - Branch-level seasonal menu scheduling
   - Pricing overrides per branch (happy hour, local promotions)

3. **Per-Branch Tables & QR Codes**
   - Tables scoped to branch (`RestaurantTable.branch_id`)
   - QR codes scoped to branch (`TableQrCode.restaurant_id` + branch context)
   - Branch-specific table codes (no cross-branch conflicts)
   - Table status visible only within branch (RLS/tenant isolation)

4. **Per-Branch Employees**
   - Employees assigned to specific branches
   - Role-based access per branch (waiter at Branch A cannot see Branch B orders)
   - Branch transfer: reassign employee to different branch
   - Central employee directory with branch affiliation

5. **Branch-Level Orders & Sales**
   - Orders belong to a branch (`Order.restaurant_id` + branch context from table)
   - Branch-level order status tracking
   - Branch-order filtering in all APIs (already partial via `restaurant_id`)
   - Orders can be transferred between branches (future)

6. **Branch-Level Reports & Comparison**
   - Sales per branch (daily, weekly, monthly, yearly)
   - Revenue comparison chart (branch vs branch vs previous period)
   - Best-selling dishes per branch
   - Order volume per branch
   - Occupancy rate per branch (tables turned, hour-by-hour)
   - Profit margin per branch (revenue minus cost of goods — if ingredient costs tracked)

7. **Centralized Owner Dashboard**
   - Overview of all branches at a glance
   - Quick stats: total revenue, total orders, active tables per branch
   - Branch performance ranking
   - Drill-down: click a branch → see its detail dashboard
   - Alerts: branch performing below threshold, low stock at specific branch

8. **Branch Manager Assignment**
   - Assign a manager to each branch
   - Manager role: full access to their branch, read-only access to other branches
   - Manager can invite staff, manage schedules, view their branch reports
   - Owner retains super-admin access across all branches

9. **Consolidated Financials**
   - Group revenue across all branches
   - Consolidated profit/loss (if ingredient costs tracked per branch)
   - Tax reporting across all branches
   - Export: all branch data in single report

## Technical Design

### Database Changes (already partially done)
- `RestaurantTable.branch_id` — already exists, FK to `restaurants.id` ✅
- All existing tables already have `restaurant_id` ✅
- No schema changes needed for Phase 10-12 if using `restaurant_id` + branch context

### API Extensions (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v1/branches` | Create branch under restaurant |
| `GET /api/v1/branches` | List branches for restaurant |
| `GET /api/v1/branches/{id}` | Get branch detail |
| `PATCH /api/v1/branches/{id}` | Update branch settings |
| `GET /api/v1/branches/{id}/dashboard` | Branch dashboard summary |
| `GET /api/v1/dashboard/all-branches` | Owner: summary of all branches |
| `GET /api/v1/branches/{id}/employees` | List branch employees |
| `PATCH /api/v1/branches/{id}/employees/{uid}` | Assign/reassign employee |

### Integration Points
- **Orders**: Branch determined by `RestaurantTable.branch_id` where order originated
- **Tables**: Branch from `RestaurantTable`; isolation already works via `restaurant_id` + tenant header
- **Employees**: `RestaurantMembership` extended with `branch_id` or scope field
- **Inventory**: Per-branch ingredient stock (if implementing Phase 11)
- **Dashboard**: Branch selector in UI, consolidated views
- **Audit**: All branch transitions audited (who created/changed branch, when)

### Schemas (new or extended)
- `BranchOut` — id, name, address, phone, timezone, currency, settings, status, manager_id
- `BranchIn` — name, address, phone, timezone, initial settings
- `BranchManagerAssign` — user_id, branch_id, role
- `BranchDashboardSummary` — revenue, orders, tables, status, ranking vs other branches

### Existing Schema Extensions
- `Restaurant` — add: `is_active`, `owner_id`, `created_at`, `subscription_tier`
- `RestaurantMembership` — add: `branch_id` (nullable; NULL = restaurant-level), `permissions_json`
- `User` — optional: `current_branch_id` (for UI context)

## Migration / Rollback
- New tables: `branches`, `branch_managers` (if separate from memberships)
- Extend: `restaurant` (settings), `restaurant_membership` (branch scope), `user` (current_branch)
- No table drops needed if using existing structure + new columns
- Rollback: remove branch-specific columns, revert branch APIs, reset data isolation

## Acceptance Criteria
- [ ] Owner can create a new branch under their restaurant account
- [ ] Branch has independent menu, tables, and employees
- [ ] Orders at Branch A are invisible to staff at Branch B (via `x-tenant-id` + branch_id)
- [ ] Branch-level sales reports accurate and comparable
- [ ] Owner dashboard shows all branches with quick-stats overview
- [ ] Branch manager has branch-scoped permissions (not restaurant-scoped)
- [ ] Consolidated financials across all branches compute correctly
- [ ] 100% of isolation tests still pass (no cross-tenant leakage introduced)
- [ ] Existing 73 tests continue to pass without modification

## Open Questions / Dependent Work
- Should branches share the same `restaurant_id` or have separate ones? (current design: same `restaurant_id`, distinguished by `branch_id`)
- How to handle merged/closed branches? (archive vs delete)
- Should branch pricing be per-item or per-category?
- Manager access: full branch API access or restricted subset?
- Consolidated reporting: real-time or batch (nightly)?
- Customer-facing: can a customer see all branches or only their selected branch?

## Phase Order Relative to Other Work
- **Before**: Inventory (per-branch stock if implemented), Billing (per-branch revenue), Employee roles (per-branch permissions)
- **After**: Employee/role management (assigning branch-level roles), SaaS subscriptions (branch limits per plan), Customer loyalty (per-branch purchase history)
- **Parallel potential**: Billing + Multi-branch (revenue aggregation across branches)