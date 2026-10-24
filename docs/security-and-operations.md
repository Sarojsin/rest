# Security, Reliability, Deployment, and Operations Rules

These are minimum planning requirements. Complete a threat model and security review before accepting real payments or deploying to real restaurant operations.

## 1. Threat model priorities

Protect against:

- Staff accessing another restaurant's records or using permissions outside their job.
- Customers guessing table/order identifiers or accessing another customer's status or bill.
- Copied QR codes, spam order submissions, automated abuse, and oversized requests.
- Forged or replayed payment webhooks, duplicate charges, late callbacks, and misleading browser redirects.
- Duplicate/overlapping waiter actions and race conditions at table/session/bill closure.
- Lost orders or missing notifications during network/process failures.
- Unauthorized discounts, refunds, voids, menu price changes, and stock adjustments.
- Leaked secrets/customer data in logs, analytics, mobile storage, errors, screenshots, or backups.
- Data loss, bad migrations, incomplete backups, and untested recovery.

## 2. Authentication and session security

Choose authentication flow based on the clients, but follow these rules:

- Use a maintained authentication library or carefully reviewed implementation. Hash passwords using Argon2id or another current recommended password-hashing algorithm with appropriate parameters; never invent a custom hash scheme.
- Use short-lived access credentials and rotating, revocable refresh credentials. Refresh token reuse should trigger a documented revoke/re-authentication policy.
- For a browser app, prefer `Secure`, `HttpOnly`, appropriately `SameSite` cookies on a deployment topology that supports them; protect state-changing cookie-authenticated requests against CSRF. Do not keep long-lived access/refresh tokens in `localStorage`.
- For React Native, store refresh credentials using iOS Keychain/Android Keystore-backed secure storage, not ordinary AsyncStorage. Keep secrets out of crash reports and logs.
- Require reauthentication or stronger approval for highly sensitive actions such as staff/role changes, refunds, or destructive account operations where appropriate.
- Implement login rate limits, generic authentication failure responses, safe password reset flows, account lockout/risk controls, and staff offboarding/revocation.
- MFA for owner/manager accounts is recommended for commercial deployment; choose implementation and recovery processes before launch.

## 3. Authorization and tenant isolation

- Use least-privilege permissions such as `orders.confirm_qr`, `kitchen.update`, `payments.record_cash`, `payments.refund`, `menu.manage`, `inventory.adjust`, and `staff.manage`.
- Check permissions at every API endpoint and service operation. Hiding a button or route is not authorization.
- Resolve `restaurant_id` from active membership, or from a valid QR credential on public routes. Never trust a client-supplied tenant ID.
- Scope reads, writes, reports, exports, background jobs, cache keys, audit searches, and object-storage paths by tenant.
- Use tenant-consistent foreign keys and test cross-tenant reads/writes using IDs from another tenant.
- Public customer routes should return only the minimum information needed to use the menu or view that one order's status.
- If PostgreSQL row-level security is adopted, configure transaction-local tenant context safely and add defense-in-depth tests; do not assume RLS replaces application authorization.

## 4. QR and anonymous customer access

- QR codes are public physical artifacts and can be copied. Treat the token as a table/menu locator, not proof that a person is seated or authorized to read prior table data.
- Use high-entropy random tokens and store only hashes. Support revoke/rotate; avoid predictable IDs.
- Require staff acceptance for every customer QR order in the pilot.
- Rate-limit by IP, token, and restaurant/table where appropriate; cap cart line count, quantity, note length, request bytes, and pending submissions.
- Protect against duplicate submission with idempotency and a clear client pending state.
- Give each accepted/submitted customer order a distinct, high-entropy read-only status credential. It must not grant order mutation, payment settlement, staff access, or access to another order.
- Avoid leaking status tokens in Referer headers, analytics, third-party scripts, crash reports, or access logs. Redact QR/status tokens from logs; use a token-exchange or fragment-to-session pattern if appropriate.
- Do not load arbitrary third-party scripts on sensitive ordering/checkout pages without reviewing their data access.

## 5. Online payment safety

- Build a provider adapter boundary; do not bind domain models to one provider's status names.
- Use a provider-hosted checkout/tokenization flow where possible. Never collect or store raw card numbers/CVV in the application.
- Verify webhook signatures using the provider's exact documented raw-body procedure and compare the event to the expected merchant/account, bill/payment reference, amount, and currency.
- Use unique provider event/transaction IDs, idempotency, replay handling, and safe handling for out-of-order events.
- Never mark a payment successful due only to a redirect query parameter or frontend response.
- When a provider request times out and the outcome is unknown, query/reconcile the provider before creating a new charge. Avoid duplicate charge attempts.
- Separate payment intent, provider settlement, refunds, and bill closure. Record a payment ledger and reconcile it against provider settlement reports.
- Use test/sandbox credentials in development and staging. Production credentials belong in a secret manager/environment injected by the deployment platform, not in source files.
- Obtain qualified review of local payment regulations, gateway requirements, accounting records, and applicable card/security obligations before launch.

## 6. Input validation and application security

- Validate all inputs server-side with explicit lengths, ranges, enums, nested shape limits, and semantic checks.
- Use parameterized ORM/SQL queries; never concatenate untrusted data into SQL.
- Encode output in React; sanitize user-authored rich content if rich text is ever permitted.
- Restrict CORS to known application origins; never combine wildcard origins with credentialed requests.
- Enforce HTTPS, HSTS (when deployment topology is ready), secure cookie attributes, appropriate content security policy, `X-Content-Type-Options`, and a frame policy appropriate for the site.
- Use request-size limits and timeouts; protect uploads by content validation, storage isolation, access controls, and malware scanning where appropriate.
- Pin dependencies and run Dependabot or an equivalent update process, vulnerability scans, secret scans, SAST, and license review in CI.
- Do not return internal exception messages, SQL details, filesystem paths, provider secrets, or full third-party error payloads to users.

## 7. Data handling and privacy

- Collect only data necessary for the workflow. Anonymous customer QR ordering should be possible unless the pilot demonstrates a requirement for identity/loyalty/accounting purposes.
- Define retention and deletion/export procedures before collecting phone/email, detailed access logs, or analytics.
- Redact personal/payment fields from telemetry and audit snapshots. Restrict who can view audit data and exports.
- Encrypt data in transit and use managed at-rest encryption for databases, backups, and object storage.
- Restrict production data access; prefer synthetic or anonymized datasets for development/test.
- Backups are sensitive data: encrypt, scope permissions, and test restoration, not just backup creation.

## 8. Reliability and recovery

- Treat every state-changing request as potentially retried. Design idempotency and transaction boundaries for orders, staff acceptance, bills, payment intents, cashier payments, refunds, and inventory movements.
- Do not show “accepted,” “paid,” “ready,” or “closed” until the server confirms the authoritative state.
- For network loss, show a clear disconnected/stale indicator and retry state. If durable offline writes are later required, add a local outbox with client-generated IDs, safe replay, ordering rules, and explicit “not synced” visibility; do not simulate success optimistically.
- Use connection timeouts, query timeouts, bounded retries with jitter, and circuit-breaking/backoff for external dependencies. Do not retry non-idempotent provider calls blindly.
- Use readiness/liveness endpoints appropriately. Readiness must fail when the instance cannot serve safely; liveness should not fail solely for a transient dependency issue that would cause restart loops.
- Maintain graceful shutdown and drain in-flight requests/workers where possible.
- Configure database pool limits based on the total worker/instance count so aggregate connections cannot exhaust PostgreSQL.

## 9. Observability and support

- Use structured logs with timestamp, severity, service, environment, request ID, route/template, status code, duration, and safe tenant/actor references where permitted.
- Never log authorization headers, raw tokens, passwords, reset links, full payment credentials, or unredacted sensitive webhook bodies.
- Track metrics for API error rate/latency, DB pool pressure, order submit/accept latency, pending QR age, kitchen queue age, payment success/failure/unknown states, webhook lag, duplicate/idempotency conflicts, outbox backlog, job retries, and stock reconciliation errors where applicable.
- Set alerts for elevated 5xx, database saturation, old pending QR requests, stuck payment intents, missed/failed webhook processing, outbox backlog, and backup failures.
- Use an error tracking service only after reviewing data redaction and access settings.
- Create support procedures to locate a transaction by request ID/order ID/payment reference without needing unsafe access to secrets.

## 10. Database and release operations

- Use managed PostgreSQL when practical; enable automated backups and point-in-time recovery if supported.
- Perform and document a restore test before real operations and on a schedule. Record actual recovery time and recovery point.
- Run migrations as a controlled release step, not at every application startup. Separate deployment identity/permissions from normal runtime DB credentials where feasible.
- Prefer backward-compatible expand/migrate/contract releases. Have a recovery strategy for migration and app deployment failures.
- Use separate development, staging, and production environments/secrets. Never clone production data into development without approved anonymization.
- Keep the API stateless. Do not depend on in-process memory for sessions, locks, or shared application state.
- Ensure the worker process is supervised and observable; critical background messages must be durably recorded before acknowledging the business transaction.
- Maintain a runbook for deployment rollback/forward fix, database restore, payment reconciliation, security incident, lost device, and staff access revocation.

## 11. Launch gate checklist

Before a real restaurant uses the system:

- [ ] Confirm jurisdiction-specific tax/invoice and payment requirements with qualified professionals.
- [ ] Threat model and access-control review completed.
- [ ] Tenant isolation tests pass, including cross-tenant ID attempts.
- [ ] Online payment sandbox test covers success, failure, timeout/unknown outcome, duplicate webhook, invalid signature, late callback, refund, and reconciliation.
- [ ] Concurrent order acceptance, session creation, bill issuance, and payment tests pass against PostgreSQL.
- [ ] Backup restore test completed and documented.
- [ ] Monitoring, alerts, support owner, and incident runbooks exist.
- [ ] Staff trained; the restaurant can recover from internet/device failure without losing or falsely accepting orders.
- [ ] Privacy/retention policy, access policy, and customer-facing terms are ready where legally required.
- [ ] Load and peak-hour tests reflect realistic menu, table, and order volume.
