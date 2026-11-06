# Platform Workflow Plans — Implementation Index

**Location:** `C:/Users/U S E R/.opencode/plan/`
**Source location (target):** `backend/app/plan/workflow/`
**Purpose:** Single source of truth for all pending PA-1+ workflow implementation.
**Status:** Planning (not implemented)

## Files in this directory

| File | Area | Status |
|------|------|--------|
| `00_workflow_overview.md` | Overall roadmap & dependencies | Draft |
| `01_plan_versions_entitlements.md` | Plan versions, features, limits | Draft |
| `02_tenant_entitlements_enforcement.md` | Backend entitlement enforcement | Draft |
| `03_trial_lifecycle.md` | Trial expiry, grace, notifications | Draft |
| `04_self_service_registration.md` | Restaurant owner self-registration | Draft |
| `05_automatic_billing.md` | Invoicing, renewal, payments | Draft |
| `06_usage_counters_seat_limits.md` | Usage tracking & seat limits | Draft |
| `07_restaurant_staff_roles.md` | Tenant staff roles & RBAC | Draft |

## How to use

1. Read `00_workflow_overview.md` first to understand dependencies.
2. Pick a file, implement it, then mark it `Implemented` in this index.
3. Update `current_state` → `desired_state` → `done` as work progresses.
4. Do not start implementation until the plan file is reviewed and accepted.

## Cross-cutting rules

- **Separate identity realms:** Platform admins and restaurant users never share credentials, tokens, or permissions (PA-ADR-001).
- **Backend enforcement:** Frontend hiding a feature is not security. FastAPI must enforce entitlements on every relevant operation.
- **Plan versioning:** Changing a plan's price or limits must not silently alter existing subscribers' terms.
- **No data deletion:** Cancelled/suspended tenants keep their records; access is restricted via subscription state.
- **All money in integer minor units.** All timestamps in UTC.
- **Audit everything:** Every mutation must have an audit record with actor, reason, before/after snapshots.
