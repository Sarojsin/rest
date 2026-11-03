# Phase 13 — Employee & Role Management Plan

## Objective
Enable restaurant owners and managers to create employee accounts, assign roles with granular permissions, track staff activity, and manage shifts and attendance. This completes the human operations layer of the restaurant management SaaS.

## Scope
### Implemented (Foundation)
- `RestaurantMembership` model — links `User` to `Restaurant` with `role` and `status`
- Existing role concepts: owner, manager, cashier, waiter, kitchen staff (defined in feature list)
- Tenant isolation via `x-tenant-id` header and `branch_id` on `RestaurantTable`
- User authentication via FastAPI auth dependency chain
- Audit logging via `record_audit()` called on membership actions
- Basic signup/onboarding flow exists

### New / Planned

1. **Employee Account Creation**
   - Owner/manager can invite new staff via email invite
   - Employee receives email with onboarding link to set password/accept terms
   - Employee profile: name, phone, hire date, employment type (full-time, part-time, casual)
   - Profile photo/upload support
   - Emergency contact info (optional)

2. **Role & Permission System**
   - Flexible role hierarchy beyond the 5 predefined roles
   - Permission grid: 50+ fine-grained permissions across modules
   - Example permission set:
     - `orders.view`, `orders.create`, `orders.edit`, `orders.delete`
     - `tables.view`, `tables.create`, `tables.edit`, `tables.delete`
     - `kitchen.view`, `kitchen.update`, `kitchen.serve`
     - `billing.view`, `billing.process`, `billing.refund`
     - `inventory.view`, `inventory.adjust`, `inventory.receive`
     - `reports.view`, `reports.export`
     - `branch.view`, `branch.manage`
   - Role inheritance: senior role inherits all permissions of junior role plus extras
   - Per-branch permission overriding (manager at Branch A has different scope than Branch B)

3. **Shift Management**
   - Create work shifts with start/end times, date, branch assignment
   - Employee can be assigned to multiple shifts (or have one active shift)
   - Shift overlap detection prevention
   - Shift swap request system (employee A requests swap with B, manager approves)
   - Punch clock: clock in/clock out with timestamp
   - Break tracking: start/end breaks within shift

4. **Attendance & Time Tracking**
   - Automatic hours calculation per shift (clock out - clock in - breaks)
   - Per-day, per-week, per-period hours totals
   - Overtime detection and flagging (if configured daily/weekly threshold)
   - Late/early flagging based on scheduled shift start
   - Time-off requests (vacation, sick, personal) with manager approval
   - Attendance summary report per employee

5. **Schedule Publishing**
   - Manager publishes weekly schedule
   - Employees view upcoming shifts in their dashboard
   - Push notification (future) when shift assigned or swapped
   - Shift calendar view (weekly/monthly)
   - Blackout dates (restaurant closed, holidays)

6. **Activity & Performance Tracking**
   - Per-employee sales contribution (if they input notes or manage orders)
   - Number of orders served per shift
   - Customer feedback links to employee (if provided)
   - Punctuality metrics (late/early occurrences)
   - Performance summary report for review periods

7. **Deactivation & Offboarding**
   - Soft deactivate: employee can't log in, but data retained
   - Hard deactivate: data anonymization (GDPR compliance)
   - Transfer ownership of employee's shifts and assignments
   - Exit survey and final pay report generation
   - Audit trail of all employment lifecycle events

## Technical Design

### New Models (to be created)
- `Employee` — user_id (FK to auth users), restaurant_id, branch_id (nullable), hire_date, employment_type, status, photo_url, emergency_contact
- `Shift` — employee_id, branch_id, date, start_time, end_time, break_start/end (optional), status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED), notes
- `Permission` — name (unique), category (ORDERS, TABLES, KITCHEN, BILLING, INVENTORY, REPORTS, BRANCH, EMPLOYEE), description
- `Role` — name (unique), permissions (many-to-many with Permission), is_system_role (boolean), description
- `RolePermission` — role_id, permission_id (junction table, may be replaced by many-to-many ORM)
- `TimeOffRequest` — employee_id, branch_id, start_date, end_date, reason, status (PENDING, APPROVED, DENIED), approved_by, approved_at, notes
- `AttendanceRecord` — employee_id, branch_id, date, clock_in, clock_out, break_start/end, hours_worked, overtime_flag, late_flag, early_flag, recorded_by

### Existing Models to Extend
- `RestaurantMembership` — extend with: `role_id` (FK to Role, replaces string role), `is_active`, `branch_scoped` (boolean), `inherited_permissions`
- `User` — optional: `employee_id` (FK, nullable; NULL = non-employee user like customer)
- `Audit` / `record_audit()` — already exists, will log all employee lifecycle events

### API Endpoints (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/employees` | List employees for restaurant/branch |
| `POST /api/v1/employees` | Create employee (invite) |
| `GET /api/v1/employees/{id}` | Get employee detail |
| `PATCH /api/v1/employees/{id}` | Update employee profile, status |
| `GET /api/v1/employees/{id}/shifts` | List employee shifts |
| `POST /api/v1/shifts` | Create shift |
| `PATCH /api/v1/shifts/{id}` | Update shift (clock in/out, status) |
| `GET /api/v1/shifts` | List shifts (filtered by date, employee, branch) |
| `POST /api/v1/time-off-requests` | Create time-off request |
| `PATCH /api/v1/time-off-requests/{id}` | Approve/deny time-off |
| `GET /api/v1/employees/{id}/attendance` | Attendance summary |
| `GET /api/v1/roles` | List roles and their permissions |
| `PATCH /api/v1/roles/{id}` | Update role permissions |
| `POST /api/v1/employees/{id}/deactivate` | Deactivate employee |

### Schemas (new or extended)
- `EmployeeOut` — id, name, email, phone, hire_date, employment_type, status, branch_name, role_name
- `EmployeeIn` — name, email, phone, employment_type, role_ids (or permission_ids), branch_id (optional)
- `ShiftOut` — id, employee, date, start_time, end_time, break_info, status, notes, hours_worked
- `ShiftIn` — employee_id, branch_id, date, start_time, end_time, break_start/end, notes
- `PermissionOut` — id, name, category, description
- `RoleOut` — id, name, is_system, permission_count, permission_names
- `TimeOffRequestOut` — id, employee, dates, reason, status, approved_by, approved_at
- `AttendanceRecordOut` — id, employee, date, hours, late/early flags, overtime

### Permission Grid Design (example 12 core categories × 3-5 levels each = ~40-60 permissions)
```
ORDERS: view, create, edit, delete, assign, claim, release, escalate
TABLES: view, create, edit, delete, assign, status-change
KITCHEN: view, update, serve, close-ticket, call-waiter
BILLING: view, process, refund, close-batch, view-payments
INVENTORY: view, adjust, receive-po, record-waste, low-stock-alerts
REPORTS: view, export, schedule, compare-branches
BRANCH: view, manage, create, archive, switch-context
EMPLOYEE: view, create, edit, deactivate, view-shifts, edit-shifts
```

### Integration Points
- **Authentication**: Employee login uses same JWT/MSAL flow; role determines accessible API paths
- **Shifts**: Clock in/out affects employee availability; integrated with scheduling
- **Payroll**: Hours worked data feeds payroll system (export feature)
- **Audit**: All employee actions (hire, fire, shift change, permission grant) audited
- **Outbox**: Employee events (hire, termination, shift assigned) for external HR systems
- **Branch Isolation**: Employee scoped to branch or restaurant-wide (owner only)

### Configuration
- Default role set on first restaurant setup (owner gets all permissions)
- Permission grid configurable per restaurant (not all restaurants need 60+ permissions)
- Branch-scoped vs restaurant-scoped roles
- Shift auto-cancellation rules (if not clocked out by end of day + 1hour)
- Overtime thresholds per restaurant (40/hr weekly, 8/hr daily, custom)

## Migration / Rollout Plan
- **Phase 1**: Add Role/Permission models, extend `RestaurantMembership`, create Employee model, basic CRUD
- **Phase 2**: Shift system, clock in/out, attendance tracking
- **Phase 3**: Advanced permissions, role inheritance, branch-scoped permissions
- **Phase 4**: Time-off, attendance reports, performance metrics
- **Phase 5**: Offboarding, deactivation, data retention policies

Rollback at any phase: remove new tables/columns, revert API routes, reset default roles, keep existing user access.

## Acceptance Criteria
- [ ] Owner can invite employee via email, employee sets password and logs in
- [ ] Roles can be created with custom permission sets
- [ ] Employees see only their branch's data (or all branches if restaurant-wide role)
- [ ] Shift creation with clock in/out works; hours calculated correctly
- [ ] Time-off requests flow: submit → manager approve/deny → employee notified
- [ ] Attendance records with hours, late/early flags, overtime
- [ ] Employee deactivation blocks login, retains data per retention policy
- [ ] Permission grid: at least 30 distinct permissions creatable
- [ ] All employee actions appear in audit trail
- [ ] Existing 73 isolation tests continue to pass
- [ ] 100% of new unit tests pass

## Open Questions / Dependent Work
- Integration with payroll export format (CSV, JSON, API to external payroll provider)?
- Should employee login be separate from restaurant customer QR login? (yes, different user pools)
- How to handle role inheritance across branches? (inherited from restaurant role + branch overrides)
- QR code login for employees (vs username/password) — future phase
- Performance review period configuration (monthly, quarterly, custom)
- Break law compliance per region (mandatory break intervals)

## Phase Order Relative to Other Work
- **Before**: Multi-branch (need employees per branch before branch-level role scoping), Billing (employees process payments)
- **After**: Multi-branch (employees assigned per branch), Inventory (staff can adjust stock), Reports (employee performance metrics)
- **Parallel potential**: Multi-branch + Employee (assign employees to specific branches during branch creation)