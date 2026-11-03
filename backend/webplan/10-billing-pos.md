# Phase 10 — Billing & POS Module Plan

## Objective
Enable restaurant staff to generate bills, process payments, and manage financial transactions from orders. This module completes the POS (Point of Sale) workflow that starts with QR ordering and ends with revenue reconciliation.

## Scope
### Implemented (Foundation)
- Order model with status lifecycle (PENDING_CONFIRMATION → ACCEPTED → COMPLETED)
- OrderItem with line totals, taxes, discounts in minor currency units
- `order_to_out()` serializer computing subtotal, tax, total
- Waiter order creation with kitchen ticket generation
- Public order status API (customer-facing order tracking)
- Claim/escalate/release claim flow on orders

### New / Planned
1. **Bill generation** from completed orders
   - Select which items/charges to include on a bill
   - Apply discounts and taxes
   - Calculate subtotal, tax, grand total
   - Support split payment types (cash + digital)

2. **Payment processing**
   - Cash payments: cashier records amount received, tracks change
   - Digital payments: integrate with payment providers (eSewa, bank transfer APIs)
   - Payment verification: display QR code for customer payment, auto-confirm on callback
   - Partial payments: bill can be partially paid, remainder stays open

3. **Invoice & receipt generation**
   - Generate PDF/HTML invoices with restaurant branding
   - Receipt summary with items, taxes, payment method, server name
   - Email receipt (future: via outbox/service call)
   - Print-friendly layout

4. **Payment tracking & reconciliation**
   - Track paid, unpaid, and partially paid bills
   - Payment history per restaurant
   - Daily cashier closing report
   - Reconcile recorded payments vs bank deposits
   - Refunds and voids with authorization

5. **Cashier closing**
   - End-of-day report: total sales, payment breakdown, tips/gratuities if configured
   - Outstanding bills report
   - Payment method summary (cash, eSewa, bank transfer, etc.)

## Technical Design

### Models (already partially exist)
- `Order` — status lifecycle, claim fields, revenue totals
- `OrderItem` — line items with prices, taxes, discounts
- Consider adding: `Bill`, `Payment`, `Refund` models

### API Endpoints (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v1/bills` | Create bill from order |
| `POST /api/v1/bills/{id}/pay` | Record payment against bill |
| `GET /api/v1/bills` | List bills for restaurant |
| `GET /api/v1/bills/{id}` | Get bill details |
| `POST /api/v1/bills/{id}/refund` | Process refund |
| `GET /api/v1/dashboard/revenue` | Already implemented (Phase 10 overlap) |

### Schemas (new)
- `BillOut` — bill ID, order ID, items, totals, payment status, payment time
- `PaymentIn` — payment method, amount, transaction ID, reference
- `RefundIn` — refund amount, reason, authorization
- `CashierCloseIn` — start/end date, payment breakdown

### Integration Points
- **Orders**: Bills are created from completed orders
- **Payments**: Payment provider callbacks → update payment status → outbox event
- **Dashboard**: Revenue aggregation from bills vs orders
- **Audit**: All payment/refund actions audited with `record_audit()`
- **Outbox**: Payment events emitted for external system sync

### Data Integrity
- Bill must reference a completed order or selected items
- Payment amount must not exceed bill total
- Partial payments leave remaining balance
- Refunds reduce bill balance; cannot refund more than paid
- All monetary values in minor units (cents/smallest currency unit) to avoid float issues

## Migration / Rollback
- New tables: `bills`, `payments`, `refunds` (if designed as new tables)
- Add columns to existing `orders` if tracking bill_id, payment_status
- Indexes on `restaurant_id`, `status`, `created_at` for performance
- Rollback: delete new tables, remove columns, revert API routes

## Acceptance Criteria
- [ ] Bill can be generated from a completed order
- [ ] Cash payment recorded, change calculated, bill status updated to PAID
- [ ] Partial payment leaves remaining balance open
- [ ] Digital payment QR displayed; auto-confirm on provider callback
- [ ] Refund processed, bill balance reduced, audit log entry created
- [ ] Cashier close report generates with correct totals
- [ ] All payment actions appear in audit trail
- [ ] 100% of integration tests pass with test DB

## Open Questions / Dependent Work
- Payment provider integration (which gateways: eSewa, Stripe, PayPal, local banks?)
- PDF generation library (WeasyPrint, ReportLab, or external service?)
- Tax configuration per restaurant (already have `RestaurantSettings.tax_rate_bps` in orders.py)
- Tipping/gratuity support (optional line item on bill)
- Print receipt hardware integration (future, via service call)

## Phase Order Relative to Other Work
- **Before**: Dashboard analytics (Phase 10 partial, already implemented), KDS (already complete), QR ordering (already complete)
- **After**: Inventory deductions (when order marked COMPLETED, deduct ingredients), Multi-branch (each branch has independent billing), SaaS subscriptions (billing at tenant level)