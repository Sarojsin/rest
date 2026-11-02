# Billing & Subscriptions

**Locked (D6):** platform billing gateway is **deferred**. The MVP bills tenants manually (sales-assisted phase). The schema, lifecycle, and enforcement are built in Phase 1 where they are cheap; the gateway integration is phase-gated (optional Phase 6) and must be droppable without schema change.

## 1. Subscription lifecycle (states & transitions)

```
trialing  --(payment / manual activation)--> active
active    --(payment failure / missed manual invoice)--> past_due
past_due  --(grace ends)--> suspended        (graceful, D10)
active    --(cancel at period end)--> cancelled
cancelled --(period end)--> expired
expired   --(data retention policy)--> deletion workflow (90d)
```

- Tenant status mirrors live subscription status in `tenants.status`; one middleware gate reads it (fast path), the subscription row is the truth.
- Transitions are either automated (cron/lifecycle) or manual (platform admin) — **different code paths** (`services/subscriptions/lifecycle.py` vs `services/platform/tenant_actions.py`), never shared (one owns billing states, the other owns ops actions).
- Downgrade: takes effect at period end, tenant notified at booking + 7 days before (can de-scope branches/staff or cancel). Upgrade: immediate + prorated (when a gateway exists; manual MVP edits entitlements via override rows).

## 2. Manual-billing MVP (Phase 1–5 users)

For the first tenants the platform does not charge cards:

1. `subscriptions.billing_mode='manual'`; ops create a `platform_invoices` row manually via super admin (thin app scope, 08 §5): amount, due date, plan code.
2. Cron sends reminder emails (day −3, day 0, +3).
3. Unpaid past-due manual invoices drive `past_due` after grace (config; default 7d), then `suspended` per D10.
3. When Phase 6 lands, historical manual subscriptions convert to gateway subscriptions in a guided backfill — referential fields (`gateway_*`) already reserved.

## 3. Stripe phase spec (optional Phase 6 — build only when ≥5 paying tenants)

Scope guardrails — build these, nothing else:

| Component | Spec |
|-----------|------|
| Products | 1 Stripe product per plan; monthly+annual prices mirrored to `plans` |
| Checkout | Hosted Checkout for upgrade/activation; `subscription_id` + `customer_id` persisted |
| Webhooks | `POST /api/platform/webhooks/stripe` — separate router, separate secret; handle: `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated/deleted`, `customer.subscription.trial_will_end` |
| Idempotency | every event id -> `platform_billing_events` insert-before-process; `(provider, event_id)` unique |
| Dunning | 3 attempts/7 days (Stripe native); email day 1/3/7; suspend day 8 unless paid |
| Reconciliation | nightly job compares Stripe subscription state vs `subscriptions` rows; mismatch ⇒ ops alert, never silent mutation |
| Refunds/credits | platform admin action, requires reason, audited + emailed to owner; credits as next-invoice line |
| Tax/VAT | not built in Phase 6. If a market demands MoR, reconsider Paddle — decision recorded before Phase 6 kickoff |
| Phase 6 do-NOTs | no metered billing, no auto-upgrades, no proration API beyond std. Stripe defaults, no tax engine |

## 4. Customer-facing payments are UNCHANGED-concern separation

Restaurant↔diner payments keep the existing gateway adapter (per-tenant config, per-branch reconciliation, dependent on plan entitlement `online_payments`). Platform billing and restaurant payments share **zero code**, zero tables, zero webhooks. A refactor doctor: never pass platform checkout through the payment adapter or vice versa.

## 5. Financial data policy

- `platform_invoices` immutable after issue (`status` transitions only; corrections = new line/credit note row).
- `platform_billing_events` append-only; 7y retention (23 pending confirm).
- Every manual/gateway billing action in super admin writes `platform_audit_logs` with `reason` + result snapshot before-after (08 §3).
- Reporting (25 §6) reads only committed, settled amounts; drafts excluded.
