# Customer QR Flow

Smallest surface, highest stakes: every screen must work on a mid-range Android over flaky Wi-Fi. No auth; the token is the boundary.

## 1. Entry

- QR encodes `https://{tenant-slug}.platform.com/t/{qrToken}`.
- On load: resolve token → `table_qr_codes (token_hash, ACTIVE)` → `tables` → branch → tenant; **cross-check hostname slug == resolved tenant slug**. Mismatch ⇒ "This QR doesn't belong to this restaurant" screen. Never a redirect (redirect would be a leak vector).
- Tenant suspended/expired (D10) ⇒ explicit "temporarily unavailable" screen (with retry).
- Error states each get a dedicated screen with actionable copy: `QR_TOKEN_INVALID`, `QR_TOKEN_REVOKED` (rotated), tenant inactive, table archived. No generic 500 surfaces.

## 2. Session lifecycle

- Customer session token binds `{table_id, qr_code_id, dining_session_id, tenant_id, branch_id}` (05 §6); 30m sliding expiry; refresh-on-activity.
- Order creation attaches to the table's active dining session (or opens one when staff accepts the first order — session-open responsibility stays with staff to avoid junk sessions).
- Shared/re-scanned QR from another device ⇒ same table session (fine); staff confirm-gate is the abuse layer.
- Session close (bill settled + staff explicit close) invalidates the customer token at next action.

## 3. Menu browsing

- Fetch merged public menu for branch (10 §2) once per entry, cached in memory; refetch on focus after long background.
- Mid-session unavailability: flagged at next interaction; cart blocks that item; server re-validates anyway.

## 4. Cart & submit

- Prices are estimates (live published price); `PRICE_CHANGED` flow on drift (10 §5) — diner confirms new totals, never silently charged.
- Submit creates `PENDING_CONFIRMATION` order (idempotency key; offline → honest banner, no auto-retry mutations).
- Diner may submit multiple orders per visit; bill accumulates across the session (bill view aggregates).
- Server rejects unavailable items `ORDER_ITEM_UNAVAILABLE {item_id}` and price drift per above; rejection reason for orders never auto-faked states (UI never shows "preparing" for pending).

## 5. Tracking

- SSE per dining-session topic + polling fallback (13 §4). Status transitions staff/kitchen-driven only.
- Rejections show reason; age-coded pending queue on staff side.

## 6. Waiter request (Phase 8) — see 11 §4; diner gets claim/ack feedback states.

## 7. Bill & payment

- "View bill" appears at COMPLETED (auto-surfaced bill, unchanged current design).
- If entitlement `online_payments.enabled` (07) and branch config allows: "Pay now" → gateway hosted checkout → **browser return never marks paid** — status Pending → webhook/provider verify → "Verifying…" → confirmed.
- Payment-at-bill only (06 §4 separation); no pay-per-order in pilot.
- Bill shows itemized lines + service charge + tax per branch config; `receipt_config` shapes display.

## 8. Branding

- Diner sees the **restaurant** brand (tenant.display_name + branch name subtitle), platform only as footer "Powered by {platform}" (product decision recorded in 23).
