# Branch Model

**Premise:** the tenant is the business (billing/plans/identity); the branch is the physical location (tables/kitchen/settings/staff scoping). A tenant is never branchless — first location is always branch #1.

## 1. Branch visibility by role (experience decision, not permission decision)

| Role | Visibility |
|------|------------|
| Waiter / kitchen / cashier | **Implicit** — one home branch; no switcher by default (only if multiplicity assigned) |
| Branch manager | **Explicit within branch** — branch name shown everywhere; may configure it |
| Regional manager / owner | **Explicit + switcher** — picker with per-branch quick stats (open sessions, pending QR orders, unacked service calls); rollup views for owners |

## 2. Branch creation workflow

1. Owner/manager with `branch.manage` clicks "Add branch" → pre-flight entitlement check (07 §2) **before** the form opens; disabled state shows upgrade hint.
2. Form: name, slug (unique per tenant), timezone, currency, tax/service-charge/receipt configs, `seed_from_branch` (default: copy menu defs + settings from another branch; option: start empty).
3. Created status='active'; short branch setup checklist surfaces (same component as tenant wizard Tier 2 items, 24 §3).
4. Audit: `branch.create` entry.
5. Module-boundary note: **"copy menu from another branch" is a `catalog` module operation**, not a `tenancy` one — branch creation calls `catalog.copy_menu_between_branches(ctx, source_id, dest_id)` (cross-module call per 02 §2.1); `tenancy` owns the branch row only.

**Seeded default is the right call** — second branches usually mirror the first; the admin then adjusts. Copy is explicit (never silent inheritance of unpublished drafts: copies publish-ready defs only).

## 3. Configuration ownership (what lives where)

| Always tenant-wide | Always branch-local | Branch-local default, tenant override possible |
|---|---|---|
| legal/billing details, brand identity, plans/entitlements, users (identities global) | address/phone, timezone, currency, tax rules, receipt layout, tables+floor plan, kitchen stations/printer, session behavior, operating hours | menu item prices (via overrides table), service charge, inventory |

Inheritance rule: tenant-level change ⇒ all branches that have not explicitly overridden keep inheriting; overrides show "Inherited from tenant: X — Override?" affordance in UI so state is always visible to the user (honest-config principle).

## 4. Staff membership across branches

- `membership_branches` rows define branch access. Zero branches ⇒ tenant-level only (billing/user mgmt; no operational data). One/some/all ⇒ operational scope accordingly; "all" = tenant-wide badge in JWT `branch_ids`.
- **One role per membership for the pilot (D13):** a role applies across every branch the user can access. Per-branch differing roles are deliberately discouraged UX (confirm warning if configured later); the simpler path is what real teams need first.
- Cross-branch coverage: a Branch A waiter cannot see/serve Branch B tickets — if the restaurant wants cross-coverage, an admin adds the membership to that branch; scheduling is out of scope (`23` deferred).

## 5. Branch switching UX (owner/regional)

- Header: `Tenant — Branch` with switcher; switching persists in URL (`?branch=<slug>` deep-linkable).
- Switching **clears every cached surface** — React Query caches keyed with tenant+branch in the key, all Zustand server-derived stores reset, in-flight requests cancelled; dirty-state confirm prompt first; a ≤250ms "loading branch" screen makes the reset feel intentional (15 §3).
- Multi-tab: two branches in two tabs must both work ⇒ branch context in URL, never only in memory.

## 6. Operational scoping consequences (summary pointers)

- Kitchen board, cashier, end-of-day: per branch (`11`).
- Reports: per-branch default, tenant rollup for tenant-wide users (`25`).
- Inventory: per branch (`25 §4`).
- Service calls/QR routing: branch-scoped with intra-branch escalation only (`11 §4`, `13 §6`).
- Daily counters → `branch_daily_counters`; order/bill numbers are per branch.

## 7. Branch archival (no delete)

1. Owner clicks "Archive branch" → system checks open dining sessions, unsettled bills, pending orders/scheduled shifts.
2. Blockers listed verbatim; owner resolves (or asks platform ops via support).
3. Clean branch → `status='archived'`; hidden from switcher (toggle "Show archived"); reversible via un-archive.
4. Data fully preserved; historical reports keep resolving branch name.
5. `branch.archive` audited with reason.
