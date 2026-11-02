# Mobile (Expo) Plan

Existing: `apps/mobile` expo-router app for staff (verified `01 §1`). Customer mobile stays web-first (no native customer app in pilot).

## 1. Auth & storage

- Refresh token per (user, tenant) in `expo-secure-store`, keyed `(user_id, tenant_id)`; access in memory; rotation/reuse-detection identical to web (`05 §3`).
- PIN login + biometric unlock for shift-start speed (device-local gate over the stored refresh, never a second credential store).
- **Biometric policy (specified):**
  - *Trigger threshold:* gate at session start and at foreground after ≥5 min backgrounded — not on every interaction; waiters keep working hands-free during a shift.
  - *Fallback ladder:* biometric fail ×2 → OS device-PIN/passcode prompt; PIN fail/unavailable ×3 → full re-authentication with password (server re-auth; refresh token survives until used — rotation protects it).
  - *Device loss:* a thief holding an unlocked device can use the stored refresh **until its next rotation** — rotation-on-use + reuse-family detection (05 §3) bounds the session; defense closes via remote revoke: tenant manager (`staff.manage`) or platform ops force-logout bumps `token_version` ⇒ device's next refresh attempt fails and the app wipes its stored secrets and returns to the login screen. Mobile checks `token_version` on every refresh, never assumes local validity.
- 401/403 handling mirrors web: refresh → retry once → `PERMISSIONS_CHANGED`/`MEMBERSHIP_REVOKED` dedicated screens; `TENANT_SUSPENDED` shows restore-CTA with read session.

## 2. Tenant/branch model

- Post-login tenant resolution: last-used default; picker for multi-membership users or explicit switch.
- Store refresh in secure-store keyed by (user, tenant); tenant switch: clear React Query caches + Zustand server stores, reconnect SSE with new token (same discipline as web, `15 §2`).
- `branch_ids` from token drive home-branch selection; implicit for single-branch staff; explicitly switchable for multi-branch.

## 3. Staff surfaces per phase

| Phase | Mobile deliverables |
|-------|---------------------|
| Phase 2 | token/tenant model, switcher, membership-aware boot |
| Phase 3 | branch-scoped QR confirm queue (age colors, accept/reject w/ reason), table/session views per branch |
| Phase 4 (RLS on) | regression pass over all flows vs isolation matrix |
| Phase 5/5b | usage banner for owner/manager, suspend-state UX |
| Phase 7 | subdomain-aware deep links (notification → correct tenant URL) |
| Phase 8 | waiter request claim/ack flow |

## 4. Notifications & realtime

- Push via Expo push: payload = ids only (no PII; `13 §7`); tap → deep link carrying tenant+branch → refetch on open.
- SSE reconnect with exponential backoff; push used while backgrounded (never sole source of truth).

## 5. Offline behavior

- Honest degradation: read cached menu/session view; block mutations with clear offline banners; no automatic mutation retry without user action (`13/15` parity).
- Queue nothing silently; failed idempotent retries re-used keys prevent duplicates.

## 6. Store lifecycle `23 §4.6`

- Enforced minimum version via API `GET /config/client-versions` (tenant-agnostic platform config; also host of feature flags) — feature-gating ships fixes without store-review cycles.
- OTA updates (EAS) for JS-only fixes within store policy; native changes go through review; staged rollout plan documented in `20 §7`.
