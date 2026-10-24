# Mobile App Rules (React Native)

The mobile app is for **staff only**: waiters, kitchen, cashier, manager.
Customers use the web app. Do not add customer screens to the app.

## Stack (fixed for the pilot)

- React Native (Expo SDK, managed workflow where possible)
- TypeScript strict
- Expo Router for navigation
- TanStack Query v5 for server state
- Zustand for local UI state
- Zod for runtime validation (shared with web)
- `expo-secure-store` for tokens
- `expo-notifications` for push (via FCM/APNs)
- `openapi-typescript` + `openapi-fetch` shared with web (via `packages/api-client`)
- Jest + React Native Testing Library
- Maestro or Detox for E2E

If a hardware integration (receipt printer, kitchen printer, card terminal) is
required and not supported by Expo, eject the specific module or use a
development build — do not eject the entire app.

## App structure
app/
(auth)/login.tsx
(waiter)/tables.tsx
(waiter)/order/[id].tsx
(waiter)/pending.tsx
(kitchen)/board.tsx
(cashier)/bill/[id].tsx
(manager)/reports.tsx
(manager)/menu.tsx
_layout.tsx

text

- Screens grouped by role. Guard access in the group layout, not in each
  screen.
- Use Expo Router's typed routes.
- Role redirect on login: route to the role's home screen.

## Auth & session

- Store refresh token in `expo-secure-store` only.
- Store access token in memory (Zustand, not persisted).
- On app foreground, silently refresh; on failure, sign out and show login.
- PIN login is a first-class path for waiters and kitchen. Rate-limit on the
  client and let the backend enforce the real limit.
- Never log tokens, PINs, or gateway payloads. `console.log` is disabled in
  production builds.

## API

- Use the shared typed API client. Same rules as web: no hand-written fetches.
- Send `Idempotency-Key` on order submission and payment creation. Generate
  once per user intent.
- Never compute prices locally as the source of truth. Same rule as web.

## Offline & connectivity

- The pilot does **not** require full offline mode. The app must **degrade
  honestly**:
  - Detect offline and show a persistent banner.
  - Queue nothing automatically that could cause a duplicate order. Instead,
    block submission and tell the user to retry.
  - Show "unknown result" state when a request times out — never assume
    failure or success.
  - Cache read-only data (menu, tables) with TanStack Query's persistence so
    the app opens to something usable.
- If the plan later enables true offline, add an outbox pattern with
  idempotency keys and a sync worker. Do not ship speculative offline code now.

## Real-time

- WebSocket for waiter and kitchen: pending orders, kitchen status, ready
  notifications.
- On reconnect, refetch all active queries.
- Push notifications are a convenience, not the source of truth. The queue
  must always be visible in-app.

## Kitchen display

- Kitchen board must be readable from 1.5m. Font ≥ 20sp. High contrast. Large
  touch targets. No color-only status indication.
- New tickets animate in. Delayed tickets (> threshold, configurable per
  restaurant) are visually flagged and sorted to the top.
- Tapping a ticket moves it through `new → preparing → ready → served`. Every
  tap triggers a mutation and an optimistic update with rollback on error.

## Cashier

- Bill detail screen shows item-level totals, discounts, tax, service charge,
  payments, and remaining balance.
- Recording a cash payment is a two-tap flow: amount (pre-filled with
  remaining) → confirm.
- Card terminal payments record the method and reference; the app does not
  integrate with a card terminal for the pilot unless a specific device is
  agreed.
- Online payment status is read-only and driven by the backend. The app
  refreshes the bill when a WebSocket event arrives.

## Printing

- For the pilot, printing (kitchen or receipt) is optional. If required,
  prefer a cloud print service or a network ESC/POS printer accessible from
  the backend. Do not build printer drivers into the app.
- If local printing is required, isolate it in a single module with a clear
  interface; do not scatter printer code across screens.

## Performance

- List screens (`tables`, `pending`, `kitchen`) must handle 200+ rows without
  jank. Use `FlashList`.
- Avoid re-rendering whole screens on every WebSocket event — update only the
  affected query cache.
- Cold start to first interactive screen < 3s on mid-range Android.

## Testing

- Screen-level tests with RNTL for branching UI.
- Maestro flows for: login → view tables → create order → submit; kitchen
  accept → ready; cashier record payment → close bill.
- Manual device testing on at least one low-end Android and one iOS device
  before release.

## Code style

- TypeScript strict. No `any`.
- No `console.log` in committed code; use a `logger` module that is silenced in
  production.
- File names `PascalCase.tsx` for screens/components, `camelCase.ts` for
  utilities.
- One default export per screen file (Expo Router requirement).
- No business logic inside screens — put it in `services/` or hooks.

## Prohibited

- Customer-facing flows in the app.
- Storing tokens in `AsyncStorage`.
- Auto-retrying mutations (order submit, payment) without an idempotency key.
- Assuming a request failed on timeout — show "unknown".
- Depending on push notifications for correctness.