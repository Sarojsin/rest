# Entitlements Enforcement

**Principles (locked):** enforced server-side only · at **mutation** time, never at read · check-before-create (never roll back a created resource) · client flags are display-only.

## 1. Entitlement document shape (stored on `plans.entitlements` JSONB)

```json
{
  "branches":       { "limit": 1  },
  "staff_users":    { "limit": 10 },
  "orders_per_month": { "limit": 5000 },
  "online_payments": { "enabled": false },
  "inventory":       { "enabled": false },
  "custom_reports":  { "enabled": false },
  "api_access":      { "enabled": false },
  "qr_sessions_per_day": { "limit": 2000 }
}
```

Semantics: `limit` = numeric ceiling; `enabled` = binary feature flag; absent key = not entitled (deny). Trial plan ships generous full entitlements. Merge rule: `effective = plan.entitlements ⊕ tenant_entitlement_overrides` (override table deferred until a real customer needs it — the merge function ships now).

## 2. Enforcement points (exhaustive)

| Entitlement | Checked at | Failure |
|-------------|-----------|---------|
| branches.limit | `POST /api/v1/branches` (button disabled client-side beforehand) | `403/409?` → `409 ENTITLEMENT_EXCEEDED` |
| staff_users.limit | `POST /api/v1/memberships` | `409 ENTITLEMENT_EXCEEDED` |
| orders_per_month.limit | order creation (QR + waiter) — **soft mode, D9** (§4) | banner/overage, not block |
| online_payments.enabled | `POST /bills/{id}/online-payment` | `409 FEATURE_DISABLED` |
| inventory.enabled | all `/api/v1/inventory/*` | `409 FEATURE_DISABLED` |
| custom_reports.enabled | report endpoints tagged `feature='custom_reports'` | `409 FEATURE_DISABLED` |
| qr_sessions_per_day.limit | QR session start | soft-degrade (§4) |

Error contract (UI switches on code):

```json
{ "code": "ENTITLEMENT_EXCEEDED",
  "details": { "entitlement": "branches", "limit": 1, "current": 1,
               "upgrade_hint": "growth" } }
```

## 3. Counter implementation — Postgres, not Redis (D7)

```python
# services/entitlements/counters.py  (summary shape)
async def increment(db, ctx, metric: str, amount: int = 1) -> None:
    period = current_month_period(now(ctx.tenant_timezone))
    await db.execute(
      sa.text("""INSERT INTO usage_counters (tenant_id, metric, period_start, period_end, count)
                 VALUES (:t, :m, :ps, :pe, :a)
                 ON CONFLICT (tenant_id, metric, period_start)
                 DO UPDATE SET count = usage_counters.count + :a"""),
      {...})
```

- Increment happens **in the same transaction as the mutation** it gates — counter and business state can never disagree.
- Count read for enforcement comes from an in-process TTL cache (5s) seeded by a `SELECT count ...` — this bounds write amplification per request and tolerates DB round-trip latency; correctness is guaranteed by the transactional increment, the cache only shapes the *precheck*.
- Month rollover creates current-row lazily on first increment. Periodic reconciliation job recomputes `count` from source tables (`orders` created in period) and alerts on drift > 0.1% — self-healing audit trail.
- No Redis. If a later scale phase needs it, this API is the seam — callers never change.

## 4. Soft vs hard limit behavior (D9)

- **Hard:** `branches`, `staff_users` — structural limits, pre-checked before form submission (client disables + tooltip), re-verified on POST.
- **Soft:** `orders_per_month`, `qr_sessions_per_day` — a restaurant never loses an order to billing: at 90% show banner; at 100% accept the order and flag `overage = true` on the counter row + notify owner; super admin sees overage report (25 §6); manual MVP invoices can carry overage as a line.
- Reads are never blocked: over-quota tenants can list/export everything; only creation is gated.

## 5. Effective-entitlements resolution

```python
def effective_entitlements(db, tenant_id) -> Entitlements:  # cached 60s
    plan = live_plan_of(db, tenant_id)          # via subscriptions
    over = tenant_overrides(db, tenant_id)      # [] until the table exists
    return merge(plan.entitlements, over)
```

Snapshotted into `ctx.entitlements_snapshot` per request (short-lived); mutation-time checks always re-resolve (never trust a stale snapshot for a deny decision; fresh read is cheap post-cache).

## 6. Usage display API

`GET /api/v1/tenant/usage` → current period per metric {used, limit, percent, soft_mode} — powers the dashboard's usage banner and upgrade prompts. Owner/manager only.
