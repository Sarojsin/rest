# Security Threat Model

## 1. Threat actors

1. Malicious diner (QR tampering/abuse) 2. Malicious staff (cross-tenant snooping, self-refunding) 3. Compromised/stolen device 4. Tenant admin scope abuse 5. Platform admin mistake/malice 6. External attacker (stuffing, webhook forgery, enumeration, SQLi, SSRF) 7. Supply chain.

## 2. Threats & mitigations (T#, plan refs)

| # | Threat | Mitigations |
|---|--------|-------------|
| T1 | Cross-tenant read via guessed UUID | L2/L3 (04 §1), 404-not-403, RLS at M5, isolation matrix per PR |
| T2 | Cross-tenant write via client tenant_id | never read from client (04 §2), composite FKs (04 §4) |
| T3 | Token/QR sharing | rotatable tokens, 30m session, staff accept-gate, rate limits per token |
| T4 | Payment webhook forgery | SDK signature verify, store-first-then-process, provider reconciliation |
| T5 | Webhook replay | unique `(provider, event_id)`; append-only events |
| T6 | Customer marking payment paid | status mutated only server-side on trusted confirmation (12 §7) |
| Stolen refresh token | tenant-bound per row (`refresh_tokens.tenant_id` exists per 05 §3 even though the table is allowlisted); rotation, hashed store, ip/ua, reuse-family revoke, token_version bumps |
| T8 | Privilege escalation via roles | changes audited, pv bump immediate, owner-only for owner-grant |
| T9 | Stale JWT after deactivation | live membership + pv check per request |
| T10 | Platform admin abuse | separate realm, role matrix (08 §2), reason+audit+notify, re-auth, optional IP allowlist (env), no PII beyond contact |
| T11 | Tenant enumeration | no unauthenticated list; login response uniform timing; subdomain is public-by-design but token-bound |
| T12 | Brute force | IP+account rate limits, argon2id, uniform responses |
| T13 | SQLi | parameterized only; ruff `S`-rules; code review; typed bound params |
| T14 | SSRF via user URLs | no server-side fetch; controlled object storage uploads |
| T15 | CSRF on cookie-auth | SameSite=Lax, short-lived access in memory, same-origin API, state-changing CSRF token where policy weakens |
| T16 | XSS in menu content | sanitize rich text (pilot: plain text render), CSP headers |
| T17 | Entitlement bypass | server-side enforcement only; client flags display-only (07) |
| T18 | Suspended tenant keeps operating | gate at mutation entries, token_version bump, worker honors status |
| T19 | Webhook DoS | verify signature first, lightweight queue dispatch, rate limit |
| T20 | Cross-tenant WS/SSE leak | topic validation per subscription (13 §4) |
| T21 | Sensitive data in logs | redaction list, structured logging, no tokens/cards/PII in event payloads |
| T22 | Overly broad DB role | non-owner app role; append-only tables get a restricted role (`revoke update/delete`) |
| T23 | Secret leakage | env/secret manager only; commit scanning; rotation runbook |
| T24 | Exfil by export | per-plan export permission, audited, rate-limited (25 §5) |
| T25 | Backup cross-tenant leak | encrypted backups, restore drill verifies isolation (20 §5) |

## 3. Secure defaults

- Deny-by-default routes: `require_permission` (or explicit `public=True` in the route manifest) — unprotected route fails CI (18 §3).
- Repositories require `ctx` (18 §3). Middleware response-asserts tenant match (02 §5).
- Password hashing argon2id; old bcrypt rows re-hashed on login transparently.
- File uploads: type/size allowlist, object keys not user-controlled, images via CDN URL allowlist domains.
- Admin step-up re-auth (60m) for destructive actions (08 §1).
- Incident response runbook in `20 §8` — includes cross-tenant leak disclosure protocol.

## 4. Privacy / compliance posture

- PII inventory: staff (name/email/phone) + customer anonymous by default — residency fields reserved (`tenants.data_region`).
- Erasure cascade per tenant: Phase-10 task; retention: audit & payment events 7y, platform audit 3y (23 pending CONFIRM with counsel).
- GDPR-style exports are the tenant's entitlement (25 §5); DPA/ToS = commercial track, out of engineering scope, listed in `23`.
