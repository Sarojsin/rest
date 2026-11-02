# Onboarding, Trials & Demo Tenant

## 1. Doors into the platform (D11: all converge on the same path)

| Door | Who / how |
|------|-----------|
| A Self-serve | marketing form → tenant `pending` + magic link → wizard |
| B Sales-assisted (pilot default) | platform admin creates shell + invite from super admin (08 §4) |
| C Migrated | existing pilot restaurant via M2 backfill → receives "here's what changed" email, skips most of wizard (24 §6) |

No path is privileged: first tenant goes through B/C, never bypasses plans/audit/trial.

## 2. Setup wizard (the highest-value workflow in the product)

| Tier | Requirements | Effect |
|------|--------------|--------|
| 1 — dashboard unlock | restaurant name + first branch, timezone, currency, tax mode, owner password | dashboard visible with checklist |
| 2 — serve a customer | ≥1 table ⇒ QR, ≥1 category, ≥1 published menu item, ≥1 staff invite (owner can self-serve as staff for testing) | features activate per-item; missing table blocks QR (clear prompt), never app-wide blocks |
| 3 — scale | full menu import, floor plan, roles beyond seed, payment gateway config, receipt template | "recommended" prompts only |

Behavior: progressive; checklist deep-links; abandonment queue (7d email nudge, 30d soft-archive no-billing, 90d deletion workflow with 7d recovery). Incomplete never blocks beyond the specific tied feature.

## 3. Trial lifecycle

- `trial` plan row: full entitlements (generous), duration per-tenant config (14/30d).
- Banner choreography: "X days left" persistent (owner-visible only — staff unaware of business model), CTAs at 7/3/1 days by email+banner escalation.
- Expiry: dashboard read-only for owner (export always allowed), customer QR "temporarily unavailable", email reactivate CTA; 7-day post-expiry grace still export-enabled.
- Data retention after expiry: 90 days → deletion workflow; never silent deletion without final email.
- **Conversion — manual-MVP flow, end-to-end (each step owned, none hand-waved):**
  1. Owner clicks "Choose plan" → plan comparison (entitlements side-by-side) → confirm.
  2. Checkout state (manual MVP): dialog states plainly — *"We'll email you an invoice within 1 business day. Your trial continues for 7 more days, so nothing changes yet."* No dead-end screen; the CTA becomes "View billing status."
  3. System transactionally: creates subscription (`status='trialing'`, extended `current_period_end = trial_end + 7d`), opens `platform_invoices` row (`status='open'`, due = +1 bd), raises an ops task in the platform admin queue (08 §5).
  4. **Ops SLA:** invoice (PDF + bank-transfer instructions from ops config) emailed within 1 business day; SLA breach visible as an aging "unemailed invoice" alert in the thin admin.
  5. Owner pays by bank transfer → **ops marks the invoice `paid`** ⇒ same transaction flips subscription → `active` (billing_mode='manual'), tenancy banner clears, confirmation email. From "Choose plan" to system-`active` there is always exactly one blocking actor (ops), visible on both sides.
  6. **Non-payment ladder:** day 7 amber banner "Conversion pending payment — finish paying the invoice"; day 14 → `past_due` per 06; day 21 → suspended per D10 (graceful; export always allowed).
  7. Phase 6 replaces steps 3–5 with hosted Checkout on the same state umbrella — tenant-facing steps change, the ladder (6) and statuses do not.

## 4. Demo tenant

- Single shared tenant (`is_demo=true`), seeded nightly reset job; login chips per role; public `demo.platform.com/t/{token}` for marketers.
- Reset job implementation guardrail: it is a scheduler job (02 §2.5) — per-tenant transactions with `app.current_tenant_id` set (RLS-scoped, not exempt); global cleanup paths use the audited bypass role with a `platform_audit_logs` entry per run (04 §8). The reset is covered by the worker-seam test (`18 §8`) — a demo reset that widens access or leaks real tenant data is a launch blocker.
- Runs under the exact same isolation (RLS, isolation tests reference it 18 §7); excluded from analytics/revenue/billing; never suspended; special "demo" plan with unlimited entitlements.
- Optional fresh-tenant sandbox seeding reuses demo dataset ("try with sample data" toggle in wizard).

## 5. First-30-minutes rule

Target metric: pilot tenant sees own menu + logs first test order within 30 minutes of starting wizard. Instrumented as platform metric `onboarding_ttfmo` in 25 §6; regression alert if median degrades.

## 6. Migrated-tenant specifics (Path 1, D11)

- Pre-migration comms template; URL changes redirect (90 days, 14 §5/11); QR reprint not needed; the owner-onboarding call is a human workflow owned by ops — its checklist lives in the commercial runbook, not engineering docs (23 §3).
