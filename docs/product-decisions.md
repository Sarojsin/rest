# Product Decisions, Assumptions, and Open Questions

**Purpose:** Prevent planning assumptions from being mistaken for confirmed requirements.

## 1. Confirmed decisions

| Topic | Current decision |
|---|---|
| Initial market | One small-to-medium family restaurant as the pilot |
| Commercial strategy | Validate with the pilot, then sell a reusable product to other restaurants |
| Initial service model | Dine-in; takeaway/delivery are not in the committed first scope |
| Overall product scope | Restaurant management, not just a basic POS |
| Staff roles | Waiter, kitchen, cashier, owner/manager experiences are required in the product plan |
| Staff mobile | React Native app for waiter, kitchen, and cashier experiences |
| Customer/manager website | React website; customer QR ordering runs in the browser, and a protected manager experience may be included/deployed separately |
| Backend | FastAPI API service |
| Customer ordering | Customer scans a table QR code and orders via a website; no app install required |
| QR acceptance | Every QR-submitted order must be confirmed by staff before entering active kitchen workflow |
| Payment channels | Support online payment and payment at the cashier |
| Shared data | All interfaces operate on the same authoritative restaurant/order/bill/payment records |
| Coding status | Planning only so far; no implementation has been specified or validated |

## 2. Proposed implementation details (framework choices vs. internal libraries)

**Confirmed framework choices:** React website, React Native staff app, FastAPI backend.

The following are engineering recommendations to approve during implementation planning, rather than choices explicitly made by the product owner:

- TypeScript for both React clients.
- Pydantic v2, SQLAlchemy 2.x, and Alembic for API validation/ORM/migrations.
- PostgreSQL as the source of truth.
- A modular monolith for the initial backend.
- Tenant scoping from the first schema, with only one active pilot tenant initially.
- One bill per dining session for the first version; no customer bill-splitting UI until validated.
- QR orders require staff acceptance; waiter-created orders may be accepted as part of the authorized “send to kitchen” action.
- Payment state remains separate from order and kitchen state.
- Staff UI should explicitly show when the server has not acknowledged an operation.

## 3. Unresolved decisions that block or materially affect implementation

### Operations and customer experience

1. **Restaurant size and flow:** actual table count, meal periods, staff count, average and peak orders per hour, and current workflow.
2. **Table/session opening:** will a waiter explicitly open a table session, or should staff acceptance of the first QR order open one automatically? Recommended: staff acceptance atomically attaches the first accepted order to an active session or creates one.
3. **Customer identity:** anonymous order tracking versus phone/name verification. Recommended: collect the minimum data needed; avoid compulsory account creation for a dine-in QR order.
4. **QR security:** static table QR codes are convenient but can be copied. Decide whether table-level tokens plus staff acceptance/rate limits are sufficient for the pilot, or whether a per-session confirmation code is required.
5. **Order modifications:** specify when a customer may request changes, who approves them, and how amendments after kitchen acceptance are handled.
6. **Kitchen operations:** one kitchen screen or printer; item-level versus ticket-level readiness; whether multiple kitchen stations are needed.
7. **Offline expectations:** whether waiters must be able to create orders when connectivity is down. Recommended initial safe behavior: cache read-only reference data and clearly disable/queue critical writes until a durable, observable retry design is approved. Never show an unacknowledged offline order as accepted.
8. **Hardware:** tablets, printers, cash drawer, and required receipt formats.

### Payment and accounting

9. **Gateway and region:** select supported providers after confirming the restaurant's country, settlement account, fees, API/webhook capabilities, refunds, and sandbox access. Do not hardcode a provider in the domain model.
10. **Payment timing:** not yet decided. Recommendation: allow online payment against a confirmed, stable bill after staff acceptance and when the customer requests checkout; also permit cashier settlement. If prepayment is later required, define behavior for rejection, item changes, cancellation, and refunds first.
11. **Price/tax snapshot policy:** determine whether menu price and tax are locked at submission or at staff acceptance. If the amount changes while a QR order is pending, the customer must be shown the revised total and approve it before acceptance.
12. **Payment variations:** multiple payments against one bill may be supported internally, but split-bill allocation across multiple diners and mixed tender should be a separate explicit requirement.
13. **Currency, tax, invoices:** confirm local rules with a qualified accountant/tax adviser. Do not assume a tax rate or invoice format. The system should make currency/timezone/tax configuration explicit and retain transaction-time snapshots.
14. **Tips/service charge/discounts:** determine whether these are used and who can authorize them.
15. **Cash reconciliation:** clarify whether there are cashier shifts, cash float counts, cash drops, and end-of-day closing procedures.

### Inventory and reports

16. **Inventory release:** core menu/order/bill workflows should be validated before promising precise ingredient accounting. Confirm whether recipes, unit conversion, wastage, supplier purchase orders, and stock counts are required for the pilot launch.
17. **Reporting:** confirm the required definitions for gross sales, net sales, tax, discounts, refunds, cancelled items, payment settlement, and business-day cutoff. Ensure reports do not derive financial facts inconsistently.

### Architecture and commercialization

18. **Hosting and data residency:** choose region/provider after checking cost, reliability, backups, and applicable law.
19. **Web deployment:** decide whether customer ordering and owner dashboard share one React deployment or are deployed separately from the same codebase. Separate deployment origins can reduce security coupling.
20. **Authentication:** select email/password versus phone-based login and determine password reset, MFA, session lifetime, account recovery, and staff offboarding procedures.
21. **Offline/real-time approach:** choose polling, Server-Sent Events, or WebSockets for live kitchen/order updates based on scale and client support. Persistent database state remains authoritative regardless of transport.
22. **Commercial model:** subscription, setup fee, per-location fee, support contract, trial terms, and data export/termination policy.
23. **Multi-branch support:** not in the first release. Build tenant configuration cleanly, but do not implement branch accounting or cross-branch stock transfer without a validated requirement.

## 4. Recommended pilot success measures

Establish a baseline before rollout, then measure at least:

- Incorrect, missing, duplicated, and late orders.
- Median and high-percentile time from QR submission to staff acceptance.
- Order-to-kitchen and kitchen-to-ready durations.
- Billing corrections, payment discrepancies, refunds, and unsettled bills.
- Staff task completion and error rates during peak service.
- Availability and recovery behavior during network interruptions.
- Inventory variance, if recipe-driven inventory is enabled.
- Staff onboarding time and support incidents.

Do not invent target percentages until the restaurant baseline and operating volume are known. Set measurable targets with the pilot owner before declaring the pilot successful.

## 5. Scope guardrails

Do not add loyalty points, delivery routing, AI forecasting, multi-branch operations, microservices, Kubernetes, or complex accounting integrations merely because they may be useful later. Add features when customer evidence, risk reduction, or measurable business needs justify them.
