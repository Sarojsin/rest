# Mobile App Rules — React Native + TypeScript

Applies to the waiter, kitchen, and cashier mobile/tablet app. Follow root `../../AGENTS.md`, `../../docs/api-contracts.md`, and `../../docs/security-and-operations.md`.

## 1. Product and role model

- One React Native app may contain role-specific navigation and screens for waiter, kitchen, and cashier. The backend remains the authority for role permissions; client route visibility is not security.
- Do not make three independent data models or separate order stores for different roles. Each screen operates on the same backend order/session/bill state.
- Use the role returned from the authenticated membership and backend permission capabilities to shape navigation. Handle revoked roles/sessions while the app is open.
- Owner/manager reporting can be delivered in the React website unless pilot research proves mobile management is necessary.

## 2. Suggested app structure

```text
apps/mobile/src/
├── app/ or navigation/     # auth gate, role-aware navigation
├── features/
│   ├── auth/
│   ├── tables/
│   ├── waiter-orders/
│   ├── qr-pending-orders/
│   ├── kitchen/
│   ├── cashier/
│   ├── bills-payments/
│   └── settings/
├── components/
├── lib/
│   ├── api/                # typed client, refresh, retry policy
│   ├── storage/            # secure credential storage only
│   ├── formatting/
│   └── connectivity/
└── tests/
```

The choice between Expo and a bare React Native workflow is open. Expo is a reasonable starting point unless validated hardware integrations require native modules outside the available Expo/native support. Do not eject or add custom native dependencies without documenting the requirement and build/release impact.

## 3. Type safety and API client

- Use strict TypeScript and API types generated from FastAPI OpenAPI or checked in CI.
- Put requests in a typed client layer. Centralize authentication refresh, request IDs, timeout behavior, and safe error conversion.
- Do not trust device-side calculations for prices, discounts, tax, bill totals, payment status, or permissions.
- Mutations must use idempotency keys where required. Retrying a timed-out request must reuse the same key and payload.
- Do not generate a new order or payment automatically when the prior result is unknown. First reconcile/query by the known request or payment reference.

## 4. Staff workflow UX

### Waiter

- Show table/session state and relevant active orders clearly.
- Pending QR requests must be visually distinct from accepted/kitchen orders.
- Accept/reject decisions must show the order/table/items and require a deliberate action; rejection should request a reason code when practical.
- After submitting a waiter order, show “sending” until acknowledged. Do not treat a local tap as server acceptance.
- Display kitchen status and make amendments/cancellations explicit with appropriate permissions and confirmation.

### Kitchen

- Use a large, high-contrast, quickly scannable layout for tablet use. Show ticket age, table/order identifier, quantities, and instructions.
- Make NEW, PREPARING, READY, SERVED, and CANCELLED states understandable without relying only on color.
- Prevent accidental duplicate actions and ask for confirmation for destructive/ambiguous transitions.
- Refresh authoritative state on app foreground/reconnect. Notifications are hints; the backend state remains the source of truth.

### Cashier

- Show server-calculated line items, taxes/charges, currency, paid amount, and remaining balance.
- Before recording cash, require explicit amount/method confirmation and display the resulting outstanding balance.
- Do not mark online payments paid from a mobile callback or local status. Wait for trusted backend state.
- Disable conflicting pay/close actions during pending requests and handle retry/reconciliation clearly.
- Require confirmation and appropriate permission for voids/refunds/high-value discounts, with an audit reason where required.

## 5. Authentication and device storage

- Use Keychain/Keystore-backed secure storage for refresh credentials; never store secrets in AsyncStorage, logs, or Redux/Zustand/plain persisted state.
- Keep access credentials short-lived and rotate refresh credentials according to backend contract.
- Clear local private state on logout, staff membership revocation, or account switching. Avoid leaving bill/order data visible after the session ends.
- Avoid logging raw API headers, tokens, QR status credentials, payment references tied to personal data, or sensitive request payloads.
- Use reauthentication for sensitive actions if required by product/security policy.

## 6. Connectivity, offline behavior, and concurrency

The offline requirement is not yet finalized. Until a tested durable offline-write design is approved:

- Cache only non-sensitive/reference data needed for graceful UX, such as the menu/table labels, with expiry and tenant binding.
- Clearly show disconnected/stale state and disable critical actions that cannot be safely confirmed online.
- Do not display unsynced local orders as accepted, kitchen-visible, paid, or persisted.
- Preserve an operation's idempotency key after timeout/retry so network recovery does not duplicate orders/payments.
- On reconnect, refetch the authoritative order, ticket, bill, and payment state instead of blindly replaying every UI action.

If offline order creation is later required, design a durable local outbox with generated operation IDs, ordered replay, conflict handling, explicit pending-sync UI, tenant binding, data expiry/encryption, and tests for process kill/restart and duplicate replay. Never introduce this as an incidental convenience feature.

For concurrent staff devices, use server version/conflict handling. Do not assume a screen's locally cached version is current.

## 7. Notifications and live updates

- Support reconnect/resubscribe and fetch current state after coming back online or returning to foreground.
- Push notifications should contain minimal data and should not be treated as authoritative state.
- Avoid placing full order notes, personal information, bill totals, or payment details in lock-screen notifications unless a clear requirement and privacy review permit it.
- Handle app backgrounding, token refresh, expired login, and failed notification registration without losing durable backend state.

## 8. Accessibility and device support

- Test on the actual form factors the restaurant will use (phone for waiter; tablet/large screen for kitchen/cashier if selected).
- Respect dynamic text size, accessible labels, screen-reader semantics, contrast, and touch target size.
- Prevent small controls near destructive actions; separate accept/reject and paid/refund actions clearly.
- Handle keyboard/scanner/receipt-printer integrations only after hardware requirements and platform support are confirmed.
- Manage images and large lists efficiently; avoid expensive rerenders in busy kitchen ticket lists.

## 9. Testing and release gates

- Unit-test API retry/idempotency behavior, permission capability mapping, status rendering, bill amount formatting, and offline/stale state.
- Use React Native Testing Library for screen behavior.
- Use device-level E2E tests (Maestro, Detox, or a selected maintained tool) for login, role switching, accepting QR orders, kitchen transitions, cash payment, duplicate submit, token expiry, and recovery after network interruption.
- Test app termination during pending network requests, refresh-token rotation, session revocation, and tenant/account switching.
- Required CI checks: lint, format, strict TypeScript, tests, API contract check, dependency/security scan, secret scan, and a reproducible staging build.
- Keep signing credentials in the release system/secret manager. Do not commit keystores, provisioning profiles, or app-store credentials.
