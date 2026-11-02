# Reports, End-of-Day & Analytics

## 1. Inventory (per counterpart docs' inventory; scoped per branch by default, tenant rollup with `report.tenant_wide`)

| Report | Grain | Notes |
|--------|-------|-------|
| Daily sales | branch×day | net/gross, covers, avg ticket; session-based (25 §3) |
| Payments & closures | branch×day | cash/card/online; per gateway reconciliation runs |
| Cancellations & voids | branch×period | reasons breakdown |
| Kitchen timing | branch×period | prep time distribution per stage (13/25 events) |
| Staff performance | branch×membership | orders, refunds (permission-aware visibility) |
| Session analytics | branch×period | sessions/day, duration, items/session (`25 §3` primitives) |
| Service-call SLA | branch×period | ack times per 13 §6 targets |
| Entitlement usage | tenant | usage/limit per metric (07 §6 reuse) |

## 2. Cashier & open-bill views

- Per-branch default views; tenant-wide owner sees rollups grouped by branch, drill-in works via branch context.
- Bill lifecycle consistent with 11 §7 (auto bill at first order, immutable lines, multiple payments).

## 3. Reporting primitives (leverage existing abstractions)

- `DiningSession` as analytics unit — "how many sessions did Branch A have today?" is a query; sessions close out metrics.
- `branch_daily_counters` supplies fast daily numerators (order/bill numbers); daily rollup materialized at EOD (§5) so reads don't hit operational tables at scale.
- Aggregation queries always tenant-scoped indexes `(tenant_id, branch_id, created_at)` (03 §5.2).

## 4. Inventory (phase-gated, per plan entitlement `inventory.enabled`)

- Branch-scoped ingredients, purchases, waste, counts; recipe-based deduction deferred until recipes are trustworthy (explicit concern in plan);
- Purchasing adds stock; recipes deduct when enabled; counts reconcile ledger vs reality with discrepancy reports; inter-branch transfers are logged stock movements (09 §7).

## 5. End-of-day (audit-grade)

- Cashier trigger per branch: **count the physical drawer and enter the count** — this is the EOD workflow, not optional: system shows expected cash (recorded payment entries), cashier enters counted cash, difference auto-computed, discrepancy recorded with reason + responsible membership; then snapshot is created and **day locks** — late payments/refunds go to next day with cross-reference to original day. (Smart cash-drawer hardware integration is deferred — 23 §3.)
- Snapshot rows: `eod_reports (tenant_id, branch_id, business_date, lines JSONB, closed_by_membership_id, closed_at, discrepancy_total_minor)`; immutable after close; report queries prefer snapshot when present.
- `lines` is a **versioned schema**, not free-form JSONB — `EodLinesV1` (Pydantic model in `modules/reports/schemas.py`):

```json
{ "schema_version": 1,
  "sales":        { "gross_minor", "net_minor", "discounts_minor", "covers",
                    "avg_ticket_minor", "orders_total", "cancelled" },
  "payments":     { "per_method": [ { "method", "amount_minor", "count" } ],
                    "expected_cash_minor", "recorded_cash_minor" },
  "discrepancies":[ { "type": "cash|void|refund", "amount_minor",
                      "reason", "membership_id" } ],
  "service":      { "calls_total", "calls_unacknowledged", "avg_ack_seconds" },
  "sessions":     { "count_total", "count_carried_over" },
  "meta":         { "business_date", "generated_at", "source": "snapshot" }
}
```
- Immutability is a schema property: a snapshot is written **once** at close never updated; if reporting logic changes or a correction is needed, a new row is produced with `schema_version` incremented (readers dispatch on `schema_version`; old snapshots stay readable forever — audit requirement).
- EOD needs `payment.record` + branch; runs may be suppressed while unresolved in-flight sessions exist (warn, not block — carry options).

## 6. Platform analytics (super admin read-only)

| Metric | Source |
|--------|--------|
| signups/trial/active/churn counts | tenants/subscriptions snapshots |
| MRR (manual: invoiced; Phase 6: gateway) | platform_invoices |
| onboarding TTFMO median | wizard events (24 §5) |
| order volume/tenant, branch counts | usage_counters |
| overage events | usage_flags (07 §4) |
| support load | platform audit actions counts |

- Aggregations run off summary tables built by a daily rollup job (never heavy OLTP scans online; `02 §6` separate-store note honored via materialized summary tables in the same DB for the pilot).

## 7. Exports

- Per-plan entitlement; CSVs per entity + audit JSON + README; background job; 7-day signed-download; every export audited + rate-limited (19/T24); allowed even past_due/suspended (suspension grace, 04 §7) — never blocked (legal risk).

## 8. Owner "different product" view (09 §1)

- Owner home = rollup dashboards, not operational screens: branch compare (revenue, avg ticket, SLA), trend vs previous period, exports, usage.
- NOT a permission-difference alone: distinct information architecture — cashiers/waiters never see it; owners never need the floor view.
