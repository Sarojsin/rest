# Phase 8 — Waiter Request Plan

## Objective
claim/escalate/timeout real-time, rate-limited, audited. Waiter can claim orders, escalate issues, timeout after period.

## Core Features
1. **Claim Order** — Waiter claims an order, it becomes theirs exclusively
2. **Escalate Order** — Waiter can escalate to supervisor if issue cannot resolve
3. **Timeout Escalation** — After fixed period, order auto-escalates
4. **Rate Limiting** — Prevent abuse: max N claims/escalations per hour per waiter
5. **Audit Trail** — Every claim/escalate/timeout logged with user + timestamp

## Order Claim Flow
1. Waiter sees list of unclaimed orders
2. Waiter clicks "Claim" on order
3. System marks order as `claimed_by = waiter_id`, `claim_time = now()`
4. Order moves to waiter's queue
5. Audit log: `waiter_id, order_id, action: "claimed", timestamp`

## Escalation Flow
1. Waiter clicks "Escalate" on claimed order
2. System marks order as `status = "ESCALATED"`, `escalated_by = waiter_id`
3. Supervisor notified (via dashboard, email, or SMS)
4. Audit log: `waiter_id, order_id, action: "escalated", timestamp, supervisor_notified`

## Timeout Flow
1. Order claimed with fixed timeout (e.g., 10 minutes)
2. System starts countdown timer
3. If timeout expires without action: `status = "TIMEOUT"`, auto-escalate
4. Audit log: `waiter_id, order_id, action: "timeout", timestamp`
5. Order returns to available pool or goes to supervisor

## Rate Limiting
- **Per waiter**: Max 5 claims/hour, max 3 escalations/hour
- **Per restaurant**: Global rate limits across all waiters
- **Redis-backed** or DB-backed counters with TTL
- **429 Too Many Requests** if limits exceeded

## Audit Requirements
- Every action: `who, what, when, outcome`
- Logs stored in `audit_events` table
- Searchable by: `waiter_id, order_id, action, timestamp`
- Retention: 90 days minimum
- Exportable for compliance reports

## Exit Criteria
- [ ] Claim flow: `PATCH /orders/{id}/claim` — marks order claimed_by=waiter_id ✅
- [ ] Escalate flow: `PATCH /orders/{id}/escalate` — marks order escalated ✅
- [ ] Timeout: automatic after fixed period ✅
- [ ] Rate limiting: 429 responses when limits exceeded ✅
- [ ] Audit trail: every action logged with waiter_id + timestamp ✅
- [ ] 43/43 + 15/15 tests still pass ✅
- [ ] ruff: 0 errors ✅

## Key Deliverables
1. **Order claim endpoint** — `PATCH /orders/{id}/claim`
2. **Order escalate endpoint** — `PATCH /orders/{id}/escalate`
3. **Timeout logic** — Automatic after fixed period
4. **Rate limiting** — Per-waiter + per-restaurant limits
5. **Audit logging** — Every action logged with full context
6. **Waiter dashboard** — View claimed orders, timers, escalations

## Technical Details
- **Duration**: 1 week
- **Dependencies**: Phase 4 M5 (RLS + Hardening) complete; branch isolation must work
- **Concurrency**: Must handle concurrent claims — only one waiter can claim an order
- **Database**: `orders` table adds `claimed_by`, `claim_time`, `timeout_at`, `escalated_by`, `escalated_at`, `timeout_status`

## Verification Commands
```bash
# Run test suite
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Test claim flow (integration)
# Test escalate flow (integration)
# Test timeout logic (integration)
# Test rate limiting (integration)

# Verify no regressions
venv\Scripts\python.exe -m ruff check app tests alembic\env.py
```

---
*Phase 8 M8 implements waiter request management with claims, escalations, timeouts, and audit logging. Critical for restaurant operations.*