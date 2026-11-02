# Operational Workflows in Multi-Tenant Context

What stays, what changes, new rules — per operational feature. Source features verified in `01 §2`.

## 1. Serving workflow (per branch)

State machine unchanged: `PENDING_CONFIRMATION → ACCEPTED → PREPARING → READY → SERVED → COMPLETED`; kitchen stops at READY; auto-complete when last item SERVED surfaces the bill.

Changes:
- All transitions branch-scoped: a Branch A waiter cannot act on Branch B items — B's READY items simply don't appear (404-style invisibility, not "access denied").
- `orders.serve` for regional managers: they hold branch membership instead of an override; acting means entering the branch context. Consistent audit.
- Audit rows gain `branch_id` (actor_membership_id already distinguishes user vs membership).
- Mid-shift permission change (pv bump): demotion ⇒ client gets `403 + PERMISSIONS_CHANGED` on next action and the session ends gracefully with a clear message (a demotion is a "stop work now" signal, not a silent degradation); promotion ⇒ token refresh transparently continues.

## 2. Multiple orders → single consolidated bill

- Unchanged pattern; session gains tenant_id+branch_id; `issue_bill` query adds branch filter (defense-in-depth alongside id).
- Cashier open-bills view: per-branch default; tenant-wide owner sees rollup grouped by branch (25 §2).
- Diner experience stays: three orders in one visit → one bill at COMPLETED; order history view still shows the individual orders — two views, one truth.

## 3. Service calls (GUEST / KITCHEN)

- Branch-scoped queue; Branch A waiter cannot ACK Branch B calls. Cross-branch routing never happens.
- Escalation intra-branch only: waiter (0s) → branch manager (30s unack) → tenant owner (2m unack) → tenant-wide manager rollup surfaces "unacknowledged" (13 §6 has timers; kitchen-ready calls route to the branch's waiters).
- Regional manager sees rollup across member branches; acts only inside a branch context (drill-in).

## 4. Waiter-request feature (Phase 8) — separate from service calls

- New `waiter_requests` table (03 §4 deferred); different SLA + routing than generic calls: claim-to-acknowledge UX (claim within X seconds → "A waiter is on the way"; 60s unclaimed → floor manager; timeout → diner sees honest "we're delayed — please flag down a staff member").

## 5. Concurrent serving races

- Idempotent second-press behavior unchanged; uniqueness per branch (item is branch-scoped so cross-branch racing is structurally impossible).
- "Who completed" traceability now branch-comparable (report primitive for 25).

## 6. Kitchen operations

- One kitchen board per branch (stalls/stations deferred — `23`); tickets created synchronously on accept.
- Kitchen display connects per branch; ticket transitions tap-driven; delayed tickets float; `kitchen.update` + branch membership required.
- Kitchen session device auth: round-trips staff realm tokens with branch binding; no shared-kiosk permanent tokens in pilot (rotating PIN per device is a Phase-10 hardening candidate in `19`).

## 7. Billing/cashier per branch

- Bill auto-creates at first order (pre-payment workflows natural); lines immutable snapshots; multiple payment entries per bill (split-bill UX deferred).
- Online payment: auto-close when fully paid **unless** jurisdiction requires waiter confirm (branch `receipt_config.auto_close_on_paid`, JSONB knob).
- End-of-day: per branch; snapshot-locks the day's reports (25 §5).

## 8. Entitlement interaction with operations

- Order creation = counter increments are in-transaction (07 §3); soft overage never blocks mid-service (D9).
- Suspended tenant (D10): in-flight sessions finish and settle; new sessions/orders rejected via single helper `tenant_gate.require_operational(ctx)` used at the 3 entry points (QR session start, order create, pay initiation).

## 9. Amendments

- Waiter can amend after accept; amendment = separate items added / removed-items cancelled (never deleted); kitchen sees "ADDITIONAL ITEMS" ticket section; amendment removes respect availability checks.
