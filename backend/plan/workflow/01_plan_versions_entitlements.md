# 01 — Plan Versions & Entitlements

**File:** `01_plan_versions_entitlements.md`
**Area:** Plan definitions, features, limits, versioning
**Status:** Draft

---

## 1. Overview

Plans are configurable data, not hardcoded React conditions. Changing a plan's price or limits must not silently alter existing subscribers' terms. Plans are versioned; existing subscribers remain on their plan version until explicitly migrated.

---

## 2. Current State

- `platform_plans` table exists with `code`, `name`, `price_monthly_minor`, `price_annual_minor`, `currency_code`, `trial_days`, `entitlements` (JSON), `status`, `is_public`, `sort_order`.
- `entitlements` is a free-form JSON blob; no schema enforcement.
- No `plan_versions` table exists.
- No `plan_features` or `plan_limits` tables exist.
- Frontend shows plan data but does not enforce limits.

---

## 3. Desired State

| Table | Purpose |
|-------|---------|
| `platform_plans` | Plan identity (code, name, description, is_public, sort_order, status) |
| `platform_plan_versions` | Versioned prices, limits, features per plan |
| `platform_plan_features` | Features belonging to a plan version |
| `platform_plan_limits` | Usage limits belonging to a plan version |
| `platform_subscriptions` | Links tenant to a specific plan version |

---

## 4. Schema Changes

### `platform_plan_versions`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `plan_id` | UUID FK → `platform_plans.id` | |
| `version` | integer | Version number, starts at 1 |
| `price_monthly_minor` | integer | |
| `price_annual_minor` | integer | |
| `currency_code` | varchar(3) | |
| `trial_days` | integer | |
| `effective_from` | timestamptz | When this version becomes active |
| `effective_to` | timestamptz | null = current |
| `is_active` | boolean | |

### `platform_plan_features`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `plan_version_id` | UUID FK → `platform_plan_versions.id` | |
| `feature_key` | varchar(64) | e.g. `qr_ordering`, `inventory`, `advanced_reports` |
| `enabled` | boolean | |

### `platform_plan_limits`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `plan_version_id` | UUID FK → `platform_plan_versions.id` | |
| `limit_key` | varchar(64) | e.g. `branches`, `owners`, `managers`, `waiters`, `kitchen`, `cashier` |
| `limit_value` | integer | Max allowed (0 = unlimited) |

### `platform_subscriptions` updates
- Add `plan_version_id` FK → `platform_plan_versions.id` (snapshot at subscription time)
- Keep `price_snapshot_minor` as denormalized price at subscription time

---

## 5. Implementation Steps

1. Create migration for `platform_plan_versions`, `platform_plan_features`, `platform_plan_limits`.
2. Add `plan_version_id` to `platform_subscriptions`.
3. Backfill existing 4 plans (starter, growth, professional, enterprise) into version 1.
4. Create API endpoints for plan version management (create version, publish version, list versions).
5. Create API endpoints for plan features and limits (CRUD).
6. Update existing admin Plans page to show versioned data.
7. Write unit tests for plan version logic.

---

## 6. Acceptance Criteria

- [ ] Can create a new plan version without affecting existing subscribers.
- [ ] Can list all versions of a plan with their features/limits.
- [ ] Existing `platform_plans` data is preserved as version 1.
- [ ] API returns versioned entitlements when fetching a subscription.

---

## 7. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/platform/plans/{plan_id}/versions` | GET | List all versions of a plan |
| `/api/platform/plans/{plan_id}/versions` | POST | Create a new plan version |
| `/api/platform/plans/versions/{version_id}` | PATCH | Update a version (draft only) |
| `/api/platform/plans/versions/{version_id}/publish` | POST | Publish a version (makes it current) |
| `/api/platform/plans/versions/{version_id}/features` | GET/POST | Manage features |
| `/api/platform/plans/versions/{version_id}/limits` | GET/POST | Manage limits |

---

## 8. Risks & Mitigations

- **Risk:** Changing a plan version accidentally affects existing subscribers.
  - **Mitigation:** Subscriptions snapshot `plan_version_id`; changes only apply to new subscriptions.
- **Risk:** Frontend hardcodes plan names/features.
  - **Mitigation:** All feature/limit checks go through backend API; frontend displays data from API.

---

## 9. Related Files

- `backend/app/plan/super_admin/04-data-model.md` — Original data model spec
- `backend/app/modules/platform/models.py` — Existing `PlatformPlan` model
- `backend/app/api/platform/router_plans.py` — Existing plans router
