# Phase Roadmap & Exit Criteria

**Estimate model (binding):** every figure below is an **engineering week** — one senior engineer with full context, part-time review, no meeting load. **Calendar (stakeholder-facing) = engineering weeks ×1.3 + the Phase 4 wait window (mostly overlapped).** Minimum viable platform (0–5 + 5b) ≈ **16 engineering weeks ⇒ ~19–21 calendar weeks** (a second engineer pulls 5/5b/7/8 parallel ⇒ ~17–19). Critical path and parallelization map at the bottom. Do not quote 7–10 weeks to stakeholders — that number exists nowhere in this document set anymore.

## Phase 0 — Foundation & module restructure (2 wk) ⛳ CRITICAL PATH
- **Module restructure FIRST** (D14/`02 §2`): `modules/<bounded_context>/` split with table ownership map, import-linter installed and green, per-module test dirs — *before any M1/M2 code exists in the old layout.* Doing Phase 1 M1/M2 on the flat layout and re-mapping later changes Phase 0 from 2 weeks into rework.
- Postgres-first dev (01 §5 checklist); full suite green on PG; `two_tenants_full` fixture skeleton; route/event/repo manifests; lint rules (context rule, layering, naive-datetime ban); internal event skeleton (13 §0 registry, no consumers yet); DNS wildcard task opened; BLOCKING decisions answered in 23.
**Exit:** PG-green CI; import-lint green; fixture harness runs; sign-off on 02/03/04/05 recorded; `git log` shows restructure preceded M1.

## Phase 1 — Tenancy scaffolding (2.5 wk, M1+M2) ⛳ CS
- M1 tables + seeds; M2 columns + backfill + verification queries (17 §M2).
- `TenantContext` dependency + middleware; tenant-status gate helper (04 §7); `GET /api/v1/tenant`.
- `permission_version` column, idempotency scoping prep; entitlement service + counters (07) — enforcement flagged NO-OP until Phase 2/3.
- Existing app untouched (dual-write not yet needed — columns only).
**Exit:** old app fully green in new module layout; tenant isolation suite runs with documented zero-failure baseline; backfill parity report checked in.

## Phase 2 — Multi-tenant auth (3 wk) ⛳ CS
- Memberships live-read (migration from restaurant_memberships begins; parallel until M4), JWT claims upgrade (05 §2), refresh per (user,tenant) with reuse detection, switch-tenant, pv invalidation.
- Internal bus goes live with first real consumers (kitchen on `order.accepted`) — proves the D15 loop before branch work piles on.
- Web/mobile: tenant picker, cache-clear on switch, error screens (MEMBERSHIP_REVOKED etc.).
- Outbox worker running with lag metric (13 §1) — second tenant can't onboard without it.
**Exit:** one user in two tenants switches cleanly; tokens realm-separated; event-contract tests green; all existing endpoints pass.

## Phase 3 — Branch model + read-switch (4 wk, M3+M4) ⛳ CS — the risk concentration
- M3 dual-write via repo base; M4 flag-gated read switch + NOT NULL + composite FKs + uniqueness re-key.
- Branch CRUD + switcher; menu overrides + merged public menu; draft/publish flows (10 §3).
- Operational scoping per branch; daily counters re-key; isolation **and** dual-write gates live (18 §6).
**Exit:** 2-branch tenant with distinct menus; both suites green; parity verified; flag flip + rollback drill executed in staging. Budget assumption: isolation suite finds real M3 bugs — that's the 4th week.

## Phase 4 — RLS + hardening (1 wk work + 2 wk wall-clock wait, M5) — runs parallel
- Policies from manifest; role separation; `SET LOCAL` everywhere; workers per-tenant transactions; worker-seam tests (04 §8).
**Exit:** cross-tenant tests pass both modes for **2 consecutive calendar weeks** (automatic CI gate); deliberate un-scoped query proves zero rows. Engineering proceeds on Phases 5/5b during the wait window.

**Wait-clock reset rule (prevents the "Phase 5 shipped but Phase 4 never stabilized" anti-pattern):** any merge to main that regresses an RLS/isolation test **resets the 2-week green clock**. If the clock resets more than once, parallel work (5/5b/6/7/8) is **halted** until the suite is green for one full week again, then resumes. Tracked automatically by the CI gate dashboard — the reset is announced in the phase channel, never absorbed silently. This rule also means the calendar estimate treats one reset as expected (already in reserve) and more than one as a schedule re-estimation trigger (22 re-estimation rule).

## Phase 5 — Thin super admin (1.5 wk)
- Realm + router + thin app: tenant list/detail/create+invite(with `source` attribution)/suspend/reactivate/force-logout; manual invoices; audit viewer (08 §5).
**Exit:** platform admin registers a tenant; suspended tenant obeys D10 gates; every action audited + owner email.

## Phase 5b — Onboarding + trial + demo (2 wk; 24)
- Setup wizard (Tier 1–3), checklist, lifecycle cron (abandonment/trial/expiry), demo tenant seeding + **tested** nightly reset (RLS-scoped, 18 §8) + exclusion paths.
**Exit:** sales-assisted tenant reaches first order in <30 min in staging; trial end transitions verified.

## Phase 6 — OPTIONAL Stripe (3.5 wk; gate: ≥5 paying tenants; 06 §3)
**Exit:** trial→active→past_due→suspended E2E in test mode; overage report correct; reconciliation alert test.

## Phase 7 — Customer subdomain (1.5 wk; D5 — cert/DNS lead time started Phase 0)
- Wildcard TLS live; QR resolution + hostname cross-check (12 §1); per-tenant branding; no cross-tenant redirect.
**Exit:** `{tenant}.platform.com/t/{token}` works; wrong-hostname token fails safely; customer flows pass.

## Phase 8 — Waiter request (1 wk; 11 §4)
**Exit:** claim/escalate/timeout real-timed; rate-limited; audited.

## Phase 9 — M6 legacy drop (1.5 wk; gate: 2-weeks-green + backup drill)
**Exit:** `restaurant_id` dropped; renames done; isolation+e2e green; rollback rehearsal executed.

## Phase 10 — Launch hardening (2.5 wk)
- Load (18 §6): 100 tenants/500 concurrent/10k orders-hr; pen test on isolation; restore drill (20 §5); deletion/erasure cascade; runbooks+on-call; support tier.
**Exit:** performance gates met; zero critical findings open; runbook sign-off; **commercial launch ready.**

## Totals & parallelization map

- Critical path (serial, marked ⛳): **0 → 1 → 2 → 3 → (Phase-4 CI wait runs in parallel) → 9 gate window → 10** ≈ 16 eng-weeks for the MVP (0–5b), ~26 eng-weeks for the full set (0–10).
- Parallelizable off-path (needs a second engineer): 4 (once dual-write is stable), 5, 5b, 6 (when triggered), 7 (once certs are issued), 8.
- Single-engineer reality check: everything serial ⇒ ~26 eng-weeks ⇒ ~34 calendar weeks (~8 months). This is why the plan insists Phases 5/6/8 stay thin; the alternative is cutting platform scope into later hardening phases, not expanding estimates silently.
- Re-estimation rule: if any phase exits later than +50% of estimate, re-run the full roadmap in writing (stakeholder doc update via 00 §3) rather than absorbing the slip silently.

## Cross-cutting exit rule

Every phase ends with: updated docs (`docs/*` mirrors), generated clients regenerated, no failing teardown, both suites green. Phases never overlap the same tables (17).
