# Notifications, Outbox & Realtime

**Two distinct layers (D15):** (1) the **internal event bus** — cross-module commands-with-a-copy via `02 §2.3`; (2) the **external notification layer** — SSE/WS/push/email to humans and devices. Both ride one outbox table and one dispatcher; they differ in consumers, not machinery. This file now specifies internal first, external second.

## 0. Internal event contract (cross-module coupling — normative)

| Event (emitter) | Consumers | Handler effect |
|-----------------|-----------|----------------|
| `order.accepted` (operations) | kitchen → create ticket; notifications → staff fan-out | ticket rows create |
| `order.completed` (operations) | billing → surface bill; notifications | bill affordance update |
| `order.rejected` (operations) | notifications | diner reason surface |
| `kitchen.ticket_ready` (kitchen) | operations → item READY; notifications → waiters | serving flow advance |
| `payment.succeeded / failed` (payments) | bill reconciliation; notifications | ledger + customer UI |
| `bill.paid` (billing) | operations (may auto-close session per 11 §7); notifications | session close logic |
| `service_call.created` (service_calls) | notifications | branch fan-out |
| `menu.published` (catalog) | operations cache-bust; notifications -> customer apps refetch | cache invalidation |
| `membership.revoked` (tenancy) | notifications; audit | owner/PLATFORM awareness |
| `tenant.status_changed` (tenancy) | notifications; platform | gate refresh, owner email |
| `trial.ending` / `subscription.updated` (entitlements) | notifications; platform | cadence per 06/24 |

Rules (binding for every handler):

1. Handlers are **idempotent** — dedupe key `(event_id, handler_name)`.
2. Failed handler → retry with backoff → parked with ops alert; **never rolls back the emitter's transaction**.
3. Handlers call the consuming module's own public service interface (module rules 02 §2.1 still apply).
4. Every event is a registered Pydantic model with `event_version`; schema changes add version N+1 with mapper, never mutate N.
5. The isolation suite proves a worker processing tenant A's events never touches tenant B (04 §8).

## 1. Outbox contract

- Every notification/event-generating mutation writes `outbox_events` **in the same transaction** as the business change. Commit ⇒ event exists; rollback ⇒ no event (no phantoms).
- `outbox_events` gains `tenant_id`, `branch_id`, `topic`, `audience_scope` ('customer_session' | 'staff_branch' | 'owner_tenant' | 'platform'), `payload`, `deliveries` bookkeeping.
- Worker: asyncio task loop inside the API process (pilot); claims batches with `FOR UPDATE SKIP LOCKED` to be multi-instance-safe; dispatch → SSE topics + email/push per §3; marks delivered with delivery idempotency (`event_id` dedupe key).
- At-least-once delivery; clients dedupe on `(event_id)`. Never trust notifications for correctness — screens refetch on open; notifications accelerate.

## 2. Event catalog (canonical names)

| Topic | Audience | Payload core |
|-------|----------|--------------|
| `order.pending_confirmation` | staff_branch | table, items, age |
| `order.accepted/rejected` | customer_session | reason |
| `kitchen.ticket.state` | staff_branch | ticket, status |
| `bill.ready` | customer_session | bill_id, total |
| `payment.confirmed` | customer_session + staff_branch | payment_id |
| `service_call.created` | staff_branch | kind, table |
| `waiter_request.created/claimed/escalated` | staff_branch | session |
| `menu.published` | tenant (client cache-bust) | item ids |
| `subscription.past_due/updated/suspended` | owner_tenant + platform | status |
| `trial.ending/cancel/activate` | owner_tenant + platform | dates |
| `entitlement.overage` | owner_tenant + platform | metric, current, limit |
| `tenant.created` | platform | tenant slug |

Events carry resolved tenant/branch; fan-out never derives audience lazily (13 §5).

## 3. Delivery channels

| Channel | Used for |
|---------|----------|
| In-app inbox (web+mobile) | everything (always present — never push-only) |
| SSE (web) | operational surfaces, scoped topics |
| Push | mobile backgrounded staff actions (QR pending, ticket ready, calls) — deep-link carries tenant+branch context |
| Email | owner digests: billing, trial, exports, audits — not ops chatter |
| SMS | critical only: suspension warning, payment failure (if phone present) |

## 4. Realtime transport rules

- SSE as default; WS for dashboard where bidirectional needed; every realtime screen has polling fallback; on reconnect → full refetch (stale cache never trusted).
- Topics: `tenant:{id}`, `branch:{id}`, `session:{id}` — subscription validates ctx membership per topic server-side; cross-branch delivery never happens.

## 5. Fan-out & routing matrix (audience resolution is data-driven, precomputed per event)

| Event scope | Resolved recipients |
|-------------|--------------------|
| staff_branch | active memberships with an active branch access + relevant permission (e.g. `order.accept_qr` for QR pendings) |
| customer_session | that dining session's connected customers |
| owner_tenant | active memberships holding owner/manager tenant-wide roles |
| platform | platform admins by role (08 §2) |

## 6. Escalation timers (worker-driven, configurable per tenant with defaults)

| Trigger | T0 | Escalations |
|---------|----|------------|
| QR order unconfirmed | notify branch waiters | 60s → branch manager; 180s → owner; never auto-reject/accept; 300s → platform alert |
| Kitchen ticket over delay threshold | kitchen supervisor | 2m → branch manager; 5m → owner |
| Service call unacknowledged | waiters | 30s → branch manager; 2m → owner (diner sees "we're on it") |
| Waiter request unclaimed | waiters | 60s → manager; timeout → honest diner message |
| Past_due | owner email | day 3 banner; day 7 email+SMS; day 8 suspend (06) |

## 7. Reliability requirements

- Worker lag metric (events unprocessed > 30s) alerts ops in staging+prod (20 §6).
- Reboot safety: workers resume from undelivered events; batch dedupe safe.
- Push notification payload excludes PII (tokens, cards, phones never in payloads) — `19` T21 discipline.

## 8. Backpressure, retention & poison pills (normative — dinner-rush behavior)

Detection alone (§7) is not a policy. The bursty load of a restaurant at peak is the design case, so behavior under lag is specified:

**Priority tiers (event property `priority: P0|P1|P2`)**

| Tier | Events | Behavior under lag |
|------|--------|--------------------|
| P0 — money/order/state-critical | `order.pending_confirmation`, `payment.*`, `kitchen.ticket_ready`, `bill.ready`, `service_call.created`, `waiter_request.created/escalated` | never suppressed, dispatched first |
| P1 — staff decision support | escalations, `entitlement.overage`, `tenant.status_changed`, manager digests | delayed before anything else |
| P2 — cosmetic nudges | diner refresh pushes beyond the polling fallback, marketing "menu updated" nudges | **deferred silently** when lag > 30s — clients rely on the guarantee that every realtime screen has a polling fallback (§4); nothing is dropped, only deferred |

**Lag escalation ladder:** lag > 30s ⇒ P2 deference + metric; > 120s ⇒ P1 deference + ops alert + email/push lanes paused (they are async anyway); > 300s ⇒ incident (20 §6). Because lag = queue depth ÷ dispatch rate, the recovery plan is always "dispatch catches up from the head" — priority ordering guarantees P0 drains first.

**Retention & cleanup:** delivered rows deleted by cron after 7 days (configurable); undelivered rows never expire silently — a row older than 1h undelivered triggers the §7 alert even if within retriable window.

**Poison pills:** per-handler retry schedule 1s/2s/4s/8s/16s (5 attempts), then the event handler pair moves to `status='parked'` with `attempts`, `last_error`, `failed_at`; parked rows never block the queue (dispatcher skips them); a parked event fires an ops alert with the dead-letter inspection link. Replay is manual (`platform_audit_logs` entry) from the parked row's payload. Nothing retries forever; nothing is lost without a trace.

**Claim mechanics (crash safety):** dispatch batch = 50 events, claim lease = 60s (`claimed_at`/`claim_expires_at`); a crashed worker's leases expire and rows become re-claimable; handler idempotency via `(event_id, handler_name)` unique deliver-log (§0 rule 1) makes the resulting at-least-once redelivery safe. The dead-letter contract is exercised by tests: known-poison events are planted in the contract suite (18 §4.3) to prove parking + isolation.
