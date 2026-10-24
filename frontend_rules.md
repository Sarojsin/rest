# Web Frontend Rules (React)

Two React web apps share one repo and one API client:

1. **Customer web app** — mobile-first, no login, accessed via QR URL.
2. **Staff web dashboard** — owner/manager/cashier, desktop-first.

Both are React + TypeScript + Vite. Follow these rules in both.

## Stack (fixed for the pilot)

- React 18
- TypeScript strict
- Vite
- React Router v6
- TanStack Query v5 for server state
- Zustand for local UI state (auth session, cart)
- Tailwind CSS
- Zod for runtime validation of API responses and form input
- `openapi-typescript` + `openapi-fetch` to generate a typed API client from
  the backend's OpenAPI schema
- Vitest + React Testing Library + Playwright
- `eslint` + `prettier`

Do not introduce Redux, MobX, or another data-fetching library without an ADR.

## Project layout
frontend/
apps/
customer/ # QR web app
staff/ # dashboard
packages/
api-client/ # generated from OpenAPI, do not hand-edit
ui/ # shared components
config/ # env access, constants
package.json

text

- Keep the two apps separate. Do not merge them into one app with
  conditional routes — different auth, different layouts, different threat
  models.
- Shared UI goes in `packages/ui` only when it is truly reusable. Duplication
  is cheaper than premature abstraction.

## API access

- **Never** hand-write fetch calls. Use the generated `api-client`.
- **Never** trust client-side price math. Every screen that shows a total must
  eventually reconcile with a server response. While the cart is local,
  display an estimate clearly marked as such, but the order confirmation view
  uses server totals only.
- The API base URL comes from Vite env (`VITE_API_URL`). No URLs in source.
- Attach `Authorization` from the shared auth store. On 401 with
  `TOKEN_EXPIRED`, attempt one refresh, then redirect to login.
- Always send `Idempotency-Key` on order submission and payment creation. The
  key is generated once per user intent and reused on retries.

## State management

- **Server state** lives in TanStack Query only. Do not copy server data into
  Zustand.
- **Local UI state** (modals, filters, cart draft, auth session) lives in
  Zustand stores, one per domain.
- Query keys follow the pattern `[domain, ...params]`, e.g.
  `['orders', 'pending', restaurantId]`.
- Mutations invalidate the relevant query keys. Use optimistic updates only
  where the plan explicitly supports it (e.g. waiter adding an item); roll
  back on error.

## Routing

- `customer` app:
  - `/t/:qrToken/menu` — menu
  - `/t/:qrToken/cart` — cart
  - `/t/:qrToken/order/:orderId` — status
  - `/t/:qrToken/bill` — bill (when applicable)
- `staff` app:
  - `/login`
  - `/tables`
  - `/orders/pending` — QR pending queue
  - `/orders/:id`
  - `/kitchen` — kitchen display (tablet-friendly)
  - `/bills/:id`
  - `/menu`
  - `/inventory`
  - `/reports`
  - `/settings`
- Route-level code splitting. Protect `staff` routes with an auth guard.

## Auth (staff)

- Access token in memory only.
- Refresh token in `HttpOnly` cookie set by the backend. Web app never reads
  it.
- On app boot, call `/auth/refresh`; if it fails, redirect to `/login`.
- Never store tokens in `localStorage`.

## Auth (customer QR)

- No login. The URL carries the QR token. The backend exchanges it for a
  short-lived session cookie scoped to that table.
- If the session expires, show a clear "Session expired, please rescan" screen;
  do not silently retry.

## Forms

- Use `react-hook-form` + Zod resolver.
- Validate on the client for UX; the backend is the final validator. Show
  server field errors next to the relevant field using the error envelope's
  `details`.
- Disable submit while pending. Use a single `Idempotency-Key` per form
  submission attempt.

## Error handling

- All errors go through a shared `ErrorBoundary` and a `toast` for
  non-blocking errors.
- The shared error envelope from `rules/shared.md` is the only error shape you
  handle. Switch on `error.code`, never on `message`.
- Show `request_id` in an expandable "Details" section for support.
- Network errors: show a retry button. Do not auto-retry mutations.

## Real-time

- Staff app subscribes to WebSocket for pending QR orders, kitchen status,
  and payment updates. On reconnect, refetch all queries in the affected
  domain.
- Customer app subscribes to SSE for order status. Falls back to polling every
  10s.

## Styling

- Tailwind. No inline `style` except for computed values.
- Mobile-first for `customer`. Desktop-first for `staff`, tablet for kitchen
  view.
- Kitchen view: minimum readable font size 20px, high contrast, no color-only
  status indicators.
- Accessibility: semantic HTML, focus management, ARIA where needed. Every
  interactive element reachable by keyboard. Color contrast WCAG AA.

## Performance

- Route-level code splitting.
- No blocking requests on the critical path of first paint.
- Menu images: `loading="lazy"`, sized placeholders.
- Customer app must be usable on a mid-range Android over 3G. Test that.

## Testing

- Component tests with RTL for any component with branching logic.
- Playwright E2E for:
  - Customer: scan → add to cart → submit → see pending → see accepted.
  - Staff: see pending order → accept → kitchen appears.
  - Cashier: open bill → record payment → close.
- No snapshot tests as a substitute for behavior tests.

## Code style

- TypeScript strict. `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
- No `any`. Use `unknown` and Zod at boundaries.
- No `fetch` outside `packages/api-client`.
- No `console.log` in committed code.
- File naming: `PascalCase.tsx` for components, `camelCase.ts` for utilities.
- One component per file.

## Prohibited

- Storing tokens in `localStorage`.
- Computing prices or taxes on the client as the source of truth.
- Embedding restaurant settings (tax rate, currency) in the client — always
  fetch from `/restaurant/settings`.
- Trusting the QR token as identity.
- Marking anything as "paid" from a browser success screen.