# Web Frontend Rules — React + TypeScript

Applies to the React website: public customer QR menu/order experience and protected owner/manager experience if these are delivered in the same web codebase. Follow root `../../AGENTS.md`, `../../docs/api-contracts.md`, and `../../docs/security-and-operations.md`.

## 1. Product boundaries

- The customer website is browser-based and mobile-first; customers should not need to install an app.
- The manager experience is authenticated and tenant-scoped. Do not expose staff administration/reporting routes to public customer sessions.
- The website is a client of FastAPI. It must not duplicate business rules for order acceptance, totals, tax, payments, permissions, inventory consumption, or state transitions.
- Public customer menu/order state and privileged management state should use separate route layouts and explicit access boundaries. Separate deployment origins are acceptable if operationally useful.

## 2. Suggested frontend structure

```text
apps/web/src/
├── app/                    # router, providers, configuration
├── features/
│   ├── public-menu/
│   ├── customer-order/
│   ├── customer-status/
│   ├── auth/
│   ├── restaurant-settings/
│   ├── menu-management/
│   ├── staff-management/
│   ├── reports/
│   └── audit/
├── components/             # reusable UI primitives
├── lib/
│   ├── api/                # typed client, auth/CSRF, error mapping
│   ├── validation/
│   ├── formatting/         # money/time/localization
│   └── telemetry/          # redacted telemetry
├── routes/
└── tests/
```

The exact routing/build library is open. React + TypeScript with a maintainable routing solution and a server-state cache such as TanStack Query is a reasonable default. Use a form library/schema validator only when it materially improves complex forms; share API-derived types instead of inventing duplicate models.

## 3. TypeScript and API contracts

- Enable strict TypeScript (`strict`, no implicit `any`, no unchecked unsafe casts without justification).
- Generate API types/client from FastAPI OpenAPI or add a CI contract check. Do not manually redefine the same response types in multiple feature folders.
- Do not use `any` to work around uncertain API types. Narrow unknown errors and map API problem codes to user-safe messages.
- Put network calls in a typed API layer, not inside arbitrary components. Keep query keys tenant-aware and invalidate relevant caches after mutations.
- Do not hardcode prices/taxes or trust client totals. Render money returned by the API and use a consistent currency formatter.
- Handle API pagination and server-side filters; do not fetch an unbounded list for a dashboard.

## 4. Customer QR website rules

- Treat URL QR values as public lookup credentials, not staff authentication. Do not show previous orders for a table.
- Customer order status credentials must be read-only and scoped to one order. Never persist them to analytics, error reports, or application logs. Avoid forwarding them in referrer URLs to third parties.
- Show unambiguous status text: “Submitted — awaiting staff confirmation” is not the same as “Accepted” or “Preparing.”
- Disable or debounce repeated submit attempts while a request is in flight, but also rely on server idempotency; UI protection alone is not enough.
- If a network request times out and the result is unknown, retain the idempotency key and safely query/retry the same operation. Do not create a new order automatically.
- Show the price and availability as provided by the server. Before final submission, validate cart selection for a good user experience, but treat server validation as authoritative.
- Clearly explain unavailable items, rejected orders, changed items, and payment failures. A changed/repriced order requires customer acceptance if the business policy requires it.
- Minimize customer PII. Avoid mandatory sign-up unless approved as a product requirement.
- Do not install analytics/advertising scripts on ordering/payment pages without privacy/security review.

## 5. Manager experience rules

- Route guards improve UX but do not replace backend authorization.
- Hide or disable actions based on permissions returned by the API, while handling `403`/`401` even when a screen is already open.
- High-impact actions (price change, discount, void, refund, staff permission update, stock adjustment) need confirmation and clear explanations; the API must audit and authorize them.
- Use explicit loading, empty, error, forbidden, stale-data, and retry states.
- Use server-confirmed outcomes for order acceptance, payment, refund, bill issue/void, and stock updates. Never optimistically label a payment or order accepted before the API confirms it.
- Prevent stale form writes using a version/ETag where the API supports it; handle `409` conflict by reloading and explaining the conflict.

## 6. State management and component design

- Separate remote server state from local transient UI state. Avoid placing all API data in one giant global store.
- Keep components focused; move domain-specific logic into typed hooks/services, while keeping authoritative rules on the server.
- Avoid duplicated copies of the same server entity with conflicting state across routes.
- Use abort signals/cancellation for obsolete reads where supported. Avoid setting state after a component no longer needs the request result.
- Store non-sensitive preferences locally only as needed. Do not put long-lived bearer tokens or payment data in localStorage.
- If cookie auth is used, implement the agreed CSRF strategy for state-changing requests and configure same-origin/CORS behavior deliberately.

## 7. Accessibility, responsive design, and UX

- Design mobile-first for the customer menu and test on low-width devices, zoomed text, and slow networks.
- Use semantic HTML, keyboard focus order, visible focus, proper form labels, accessible dialogs, status announcements, and sufficient contrast.
- Do not use color alone to communicate item availability, order state, validation errors, or payment results.
- Ensure interactive targets are comfortably touch-sized and cart/order submission remains clear when the keyboard is open.
- Provide language/currency/time formatting based on restaurant configuration, not browser assumptions alone.
- Use image dimensions, responsive loading, and fallback text to avoid layout shift; only publish approved menu images.

## 8. Security and privacy

- Render text as text; avoid `dangerouslySetInnerHTML`. If rich menu descriptions are eventually required, sanitize using an allowlist on the server and still render safely.
- Never expose secrets in `VITE_*`/client build variables. Anything compiled into the website is public.
- Do not log complete QR/status URLs, credentials, request bodies containing private data, or gateway response payloads.
- Apply a restrictive Content Security Policy where deployment allows it; review any third-party script, font, image host, or payment integration.
- Treat uploaded image URLs, query values, and response content as untrusted.

## 9. Testing and release gates

- Unit-test business-independent UI logic, formatters, cart validation, permission-based rendering, and error mapping.
- Use React Testing Library for accessible behavior and interactions.
- Use Playwright (or an equivalent browser E2E tool) for QR-to-menu, duplicate submission, pending confirmation, rejected order, payment failure/success-state handling, login/session expiry, and permission-denied scenarios.
- Test keyboard navigation, screen-reader labels/status announcements, mobile viewport, slow network, offline, stale cache, and expired QR/status tokens.
- Required CI checks: ESLint, Prettier, strict TypeScript, unit tests, contract check, E2E smoke tests, dependency/license/security scan, secret scan, and production build.
