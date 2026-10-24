# Restaurant Management System — Product Planning Document

**Document type:** Product and requirements plan  
**Planning status:** Initial planning; no code or technology stack selected  
**Last updated:** 24 October 2026

> **How to read this document**
> - **Confirmed decision** means it follows directly from the choices made in our discussion.
> - **Proposed recommendation** means it is a sensible next step, but has not yet been formally approved.
> - **Open decision** means we still need information or a decision before treating it as a requirement.

---

## 1. Product Overview

We plan to build a commercial restaurant management system for a **small-to-medium family restaurant that primarily serves dine-in customers**. We will use one restaurant as the pilot customer, validate the system in real operating conditions, and then make the product configurable and reusable for other restaurants.

The product will connect restaurant staff and customers through a shared operational system. Staff will use role-appropriate interfaces to manage tables, orders, kitchen preparation, billing, payments, inventory, and reporting. Customers will be able to scan a table QR code, open a menu website, and submit an order without installing an app.

### 1.1 Product direction

- **Confirmed:** The initial pilot is for one restaurant.
- **Confirmed:** The target is a small-to-medium family restaurant.
- **Confirmed:** The first service model is dine-in.
- **Confirmed:** The product scope is complete restaurant management, rather than only a simple billing/POS tool.
- **Confirmed:** The business objective is commercial: pilot with one restaurant, then sell to other restaurants.
- **Confirmed:** Customers should be able to order using a QR-linked website.
- **Confirmed:** Each QR-submitted order must be confirmed by staff before it enters the active kitchen workflow.
- **Confirmed:** The product should support both online payment and payment at the cashier.
- **Open:** The exact point at which customers can initiate online payment has not been finalized.
- **Open:** The mobile/web implementation approach for staff has not been finalized.

### 1.2 Product principles

1. **One source of truth:** Waiter, kitchen, cashier, manager, and customer experiences must refer to the same underlying order and bill records.
2. **Operational reliability first:** A lost, duplicated, or incorrectly billed order is more serious than a missing cosmetic feature.
3. **Clear state transitions:** Orders, kitchen progress, and payments have related but separate statuses.
4. **Role-appropriate interfaces:** Each role should see the information and actions needed for its work, not an unnecessarily complicated all-in-one screen.
5. **Configurable business settings:** Menus, prices, tax settings, tables, staff, and other restaurant-specific data should not be hardcoded for the pilot.
6. **Validate before expanding:** Build for the pilot, measure real usage, and generalize based on evidence instead of building speculative complexity.

---

## 2. Target Customer and Operating Context

### 2.1 Initial customer profile

The expected pilot is a family restaurant with table-based dine-in service, front-of-house staff, a kitchen team, and a cashier or manager. The actual table count, number of staff, number of daily orders, busiest periods, and current business process have **not** yet been established.

These details should be collected during requirements discovery. They must not be assumed or hardcoded.

### 2.2 In-scope service model

**Initial scope:** dine-in service with table assignment and QR ordering for a table.

**Not committed for the initial release:** takeaway, delivery, delivery tracking, online marketplace integrations, or chain-wide branch operations. These may be considered later if customer research justifies them.

### 2.3 Primary business problems to investigate

The pilot discovery process should determine whether the restaurant currently experiences:

- Orders being lost, duplicated, or misunderstood between waiters and the kitchen.
- Delays caused by staff manually relaying orders.
- Incorrect bills, unrecorded discounts, or payment discrepancies.
- Difficulty knowing whether a table is occupied, ordering, waiting for food, or ready to close.
- Poor visibility into sales, popular menu items, cancellations, or staff actions.
- Inaccurate ingredient stock, unexplained wastage, or difficulty managing purchases.
- Limited visibility into order and kitchen waiting times.

These are candidate problems to validate, not claims that the pilot restaurant definitely has all of them.

---

## 3. Users, Roles, and Permissions

The system should provide role-based access. A role should determine what a user can view and what actions they can perform.

### 3.1 Customer

Customers may:

- Scan a table-specific QR code.
- View the published menu, item descriptions, prices, availability, and permitted customizations.
- Build and submit an order.
- See whether their request is awaiting confirmation, accepted, rejected, or in progress, where status display is enabled.
- Review the bill and choose a supported payment channel once the payment flow is defined.

Customers must not be able to change trusted prices, assign themselves to arbitrary tables, modify another table's order, or mark a payment as successful themselves.

**Open:** Whether customers need to provide a name, phone number, account, or other identifier has not been decided. The default should be to avoid collecting personal information that the workflow does not need.

### 3.2 Waiter

Expected responsibilities:

- View table availability and current table/order status.
- Open or access a table's order.
- Add menu items, quantities, and customizations.
- Submit an order to the kitchen workflow.
- Review kitchen statuses and mark food as served, where that action is part of the workflow.
- Help customers who do not want to use QR ordering.
- See and act on QR orders awaiting staff confirmation, subject to the final permission model.

Waiters should not automatically have unrestricted rights to refund payments, alter settled bills, or change system-wide settings.

### 3.3 Kitchen staff

Expected responsibilities:

- View accepted kitchen tickets and their item details.
- Read preparation instructions and item customizations.
- Update preparation status, for example New, Preparing, and Ready.
- Identify delayed, cancelled, or amended items.

Kitchen users should not need access to customer payment credentials, full financial reporting, or restaurant administration settings.

### 3.4 Cashier

Expected responsibilities:

- Find a table's current bill and review its items and totals.
- Record supported cashier-side payments.
- See online payment status based on trusted backend/gateway confirmation.
- Issue or reprint a receipt where permitted.
- Close a bill when the recorded balance is settled.
- View relevant shift or end-of-day payment summaries, according to permissions.

Refunds, voids, discounts above an allowed limit, and edits to settled bills should be permission-controlled and logged.

### 3.5 Manager or owner

Expected responsibilities:

- Manage menu items, prices, availability, categories, and customizations.
- Manage tables, staff accounts, roles, and permissions.
- Review sales, cancellations, discounts, payments, and operational reports.
- Manage stock, recipes, suppliers, purchasing, and stock adjustments when inventory features are enabled.
- Review audit history and approve sensitive actions.
- Configure restaurant-specific settings.

**Open:** Whether the owner and manager are separate roles, and which actions require owner-level approval, must be confirmed with the pilot customer.

---

## 4. Application and Interface Strategy

### 4.1 Customer QR website

**Confirmed direction:** A customer scans a QR code and opens a website containing the restaurant menu and ordering flow. Customers should not need to install an app merely to browse the menu and submit an order.

Expected capabilities:

- Mobile-friendly menu browsing.
- Menu categories, item descriptions, prices, availability, and allowed options.
- Cart review and order submission.
- Clear confirmation that a request was received and is awaiting staff confirmation.
- Status feedback and, later in the flow, access to the current bill and supported payment options.
- Clear error messages for unavailable items, expired sessions, failed submissions, and payment problems.

### 4.2 Staff interfaces

**User proposal:** Mobile apps for waiters, kitchen staff, and cashiers.

**Recommendation discussed, not yet confirmed:** Start with a shared responsive staff application or Progressive Web App (PWA) with role-based views. Make the waiter experience mobile-first, the kitchen screen easy to read on a tablet or larger display, and the cashier experience suitable for a tablet or desktop. This approach could reduce deployment and maintenance overhead compared with three separate native applications.

A native mobile app may be appropriate if later requirements demonstrate a need for device-specific capabilities, particular hardware integrations, or more reliable device-level behavior. This choice should follow workflow and device discovery rather than be decided only by preference.

### 4.3 Owner/manager dashboard

A web-oriented dashboard is proposed for configuration, reports, users, inventory, and audit history. Its final device support and implementation approach remain open.

### 4.4 Device and hardware discovery

Before settling the interface architecture, determine:

- Which devices the restaurant already owns.
- Whether the kitchen can use a tablet/monitor or needs a kitchen printer.
- Whether the cashier needs a receipt printer, cash drawer, barcode scanner, or other peripheral.
- Wi-Fi coverage and internet reliability in the dining room and kitchen.
- Whether staff need to operate during an internet outage.

No particular hardware vendor or device model has been selected.

---

## 5. Core Modules

The following modules form the proposed overall product scope. Their order of delivery should be refined after the pilot workflow is documented.

### 5.1 Table management

Candidate requirements:

- Represent each dining table with a unique identifier and human-readable table number/name.
- Show availability and relevant active-order state.
- Link a QR code to the appropriate table.
- Allow an authorized staff member to open a table order, add additional items, and close the table's dining session when appropriate.
- Prevent one table's QR session from freely accessing another table's information.
- Support QR-code replacement or invalidation if a code is copied, damaged, or needs to be changed.

**Open:** Whether the pilot needs table transfers, merging tables, reservations, table sections, or seating/waitlist management is not yet known.

### 5.2 Menu management

Candidate requirements:

- Menu categories and items.
- Item names, descriptions, prices, and optional photos.
- Item options and customizations, where needed.
- Availability controls, including marking an item temporarily unavailable.
- Menu publishing so changes are reflected on the customer website.
- Price and menu-change history where it is important for audit or reporting.
- Validation of current price and availability by the backend at order submission; the customer browser must not be trusted as the source of price.

**Open:** Multi-language menus, multiple sizes, add-ons, dietary/allergen labels, item-specific preparation times, and scheduled menus need validation.

### 5.3 Order and POS management

Candidate requirements:

- Create an order from the waiter interface or customer QR website.
- Associate dine-in orders with the correct table.
- Add items, quantities, options, and instructions.
- Allow an authorized staff member to modify an order before or after kitchen submission under controlled rules.
- Record order submission time, acceptance time, changes, cancellations, and the actor who performed each action.
- Protect against duplicate order submission when a device retries after a slow or failed connection.
- Make order history available for investigation and reporting.
- Keep order status separate from payment status.

The customer QR channel and waiter channel must create or update records in the same order system. They should not maintain independent, disconnected versions of an order.

### 5.4 Kitchen management

Candidate requirements:

- Receive kitchen tickets only after the relevant order has been accepted by staff.
- Display order/ticket number, table, submission/acceptance time, items, quantities, and instructions.
- Track preparation status at an appropriate ticket or item level.
- Support New, Preparing, and Ready as an initial status model, with a policy for cancelled or amended items.
- Notify the waiter when items are ready, using a mechanism supported by the selected interface and network design.
- Highlight old or delayed tickets.
- Preserve a clear record of changes made after a ticket enters the kitchen.

**Open:** Whether one order should become one kitchen ticket or be routed to multiple stations (for example, drinks and hot food) depends on the pilot kitchen layout.

### 5.5 Billing and cashier operations

Candidate requirements:

- Build a bill from the restaurant's accepted order items and applicable adjustments.
- Display item-level totals and the bill total clearly.
- Apply configurable tax, service charge, and discount rules once the restaurant's legal and business requirements are confirmed.
- Support the approved cashier payment methods.
- Keep a record of payments, refunds, voids, and adjustments.
- Prevent closing a bill while an amount remains outstanding, except through an explicit, authorized process for an agreed exception.
- Generate receipts and support reprinting where needed.
- Provide cashier and end-of-day reconciliation summaries.

**Open:** Tax rules, required invoice fields, receipt format, tipping/service-charge policy, discounts, refunds, and whether partial payments are needed must be validated against the pilot's business and legal context.

### 5.6 Online payments

**Confirmed:** Online payment is in scope, alongside payment at the cashier.

Candidate requirements:

- Integrate with a supported payment gateway once the market, available provider, merchant requirements, and fees are known.
- Verify payment through a trusted backend/gateway confirmation mechanism. A success screen in the customer browser alone is not proof of payment.
- Handle pending, successful, failed, cancelled, delayed, and refunded payments.
- Make payment processing idempotent so gateway retries do not create duplicate payment records or duplicate charges where the provider's mechanisms can prevent them.
- Reconcile application records with gateway transactions.
- Never ask the application to store raw card credentials; use the provider's approved checkout flow and security requirements.
- Keep the order and payment lifecycles distinct. An accepted or preparing order can be unpaid, and a completed order must not be considered paid merely because it was served.

**Open — critical:** The point at which a customer can pay online is not finalized. Options include paying immediately after staff accepts the order, paying when the bill is requested, or supporting both according to a defined policy. The recommendation discussed was to wait until staff has accepted the order and its items/total are confirmed, with payment available when the bill is requested. This remains a recommendation, not a confirmed decision.

### 5.7 Inventory and purchasing

Inventory is part of the intended complete-management scope. The detailed rollout order still needs confirmation.

Candidate requirements:

- Ingredients or stock items with units of measurement.
- Stock received from purchases and suppliers.
- Stock movements for use, waste, corrections, and returns where applicable.
- Menu recipes or ingredient mappings so expected ingredient usage can be estimated from sold items.
- Low-stock thresholds and alerts.
- Supplier records and purchase history.
- Stock counts and discrepancy reports.
- Permissions and audit records for manual stock adjustments.

Accurate recipe-based inventory requires reliable ingredient quantities, unit conversions, recipe definitions, and records of wastage and corrections. It should not be presented as exact merely because a sales item exists in the menu.

**Proposed staged approach:** Start by validating stock items, stock-in/stock-out records, stock adjustments, and purchase recording. Add recipe-based consumption and deeper cost/profitability reports after the restaurant's recipes and operational practices have been documented.

**Open:** Whether stock deductions should occur on order acceptance, preparation, serving, or another event must be decided. Waste, returned items, cancelled dishes, and recipe changes must be addressed in that decision.

### 5.8 Staff and permissions

Candidate requirements:

- Individual staff accounts rather than a shared, untraceable login for sensitive actions.
- Role-based permissions.
- Appropriate restriction of refunds, bill changes, discounts, stock corrections, user management, and settings.
- Recording the responsible user and time for meaningful operational and financial changes.

**Open:** Staff attendance, shift management, payroll, scheduling, and performance targets are not committed to the initial release.

### 5.9 Reports and audit history

Candidate reports:

- Daily sales and order counts.
- Sales by menu item/category and time period.
- Payment totals by method and reconciliation differences.
- Cancelled items/orders, refunds, discounts, and voids.
- Order waiting times and kitchen preparation times.
- Stock balances, purchases, waste, and stock discrepancies when inventory is enabled.
- Staff actions relevant to operational and financial accountability.

Reports should distinguish gross sales, discounts, taxes/charges, refunds, and collected payments according to defined business rules. A sales total is not automatically the same as money collected or profit.

---

## 6. Customer QR Ordering — Confirmed Workflow Direction

### 6.1 Proposed flow

1. The customer scans the QR code associated with a table.
2. The website opens the menu for that table.
3. The customer selects items, quantities, and available customizations.
4. On submission, the system validates the table reference, current menu state, prices, quantities, and item availability.
5. The system creates a pending request and displays that it is awaiting staff confirmation.
6. Authorized staff review the request.
7. Staff either accept it or reject it. Rejections should have an appropriate reason where useful, and the customer should receive clear feedback.
8. On acceptance, the order enters the active kitchen workflow and the kitchen ticket is created or made available.
9. The customer can receive status updates where the status interface is implemented.
10. Payment follows the final policy to be decided; online and cashier payment are both intended to be supported.

### 6.2 Acceptance and rejection

- **Confirmed:** Staff must confirm each QR-submitted order before it enters the active kitchen workflow.
- A pending request is not yet a kitchen-preparation instruction.
- Staff should be able to see the table, items, customizations, submission time, and current menu/pricing context.
- Staff should be able to reject a request, for example when an item is unavailable or the request is invalid.
- If staff proposes substitutions or changes the requested items/total, the product needs a clear customer approval policy. This policy is not yet finalized.
- Pending requests should be visible in a queue and should not silently disappear.
- The product should protect against repeated submissions from a double tap or a client retry.

### 6.3 QR safety and privacy

A table QR code identifies a table, but it should not be treated as proof of customer identity or payment. QR codes can be photographed or shared.

Proposed safeguards:

- Use table-specific references that are not trivial to guess.
- Avoid displaying another table's order details through a copied or manipulated QR URL.
- Allow the restaurant to invalidate or replace a QR code.
- Apply reasonable submission limits and provide staff with controls to reject suspicious requests.
- Avoid collecting customer personal information unless there is a justified requirement.

**Open:** Whether to require a customer name, phone number, one-time table session, or another way to associate follow-up requests with the correct visit is not decided.

---

## 7. Order, Kitchen, Table, and Payment States

The following are proposed starting models and must be tested with the pilot's real workflow.

### 7.1 QR request / order progression

A candidate progression is:

`Submitted → Awaiting staff confirmation → Accepted → Preparing → Ready → Served`

Alternative terminal or side states include `Rejected` and `Cancelled`.

Important rules:

- The interface must not tell a customer that food is being prepared before staff accepts the request and the order enters the kitchen workflow.
- The implementation should define which roles may transition each status.
- Cancellation after kitchen preparation begins must not be treated like deleting an unsubmitted cart.
- Changes to accepted items should be communicated to the kitchen and recorded.
- Order status transitions should be validated by the system, not accepted as arbitrary text from a client.

### 7.2 Payment progression

Payment must have its own status. Candidate values include `Unpaid`, `Pending`, `Partially paid` (if partial payments are supported), `Paid`, `Failed`, `Cancelled`, and `Refunded` or `Partially refunded`.

This is a proposed vocabulary, not a finalized database design. The final model should represent multiple attempts and transactions accurately where necessary rather than overloading one status field.

### 7.3 Table progression

Candidate table statuses include `Available`, `Occupied`, and `Needs cleaning` or an equivalent post-service state. The correct table status should derive from the actual dining-session workflow, not be changed solely because a customer opens a QR page.

**Open:** Whether to include `Reserved`, `Waiting for bill`, table transfers, or multiple active parties at one table is not decided.

---

## 8. Cross-Cutting Functional Requirements

### 8.1 Consistency across interfaces

- A waiter-created order and a QR-created order must enter the same operational system.
- All roles should see relevant changes without maintaining separate independent copies of the order.
- Prices and payment status must come from trusted server-side records, not from values supplied by the customer browser.
- The product must preserve meaningful order, bill, and payment history.

### 8.2 Failure handling and duplicate protection

The system should plan for slow or interrupted connections, repeated button taps, delayed gateway confirmation, and retrying clients.

- Show whether an order submission was received or whether the result is unknown because of a network problem.
- Use safe retry behavior so the same submission is not accidentally accepted twice.
- Do not mark a payment paid solely because a browser redirected to a success page.
- Make pending or failed payment conditions visible to the cashier/authorized staff.
- Provide a clear recovery procedure for interrupted devices or delayed notifications.

**Open:** Full offline operation (allowing order entry during an internet outage and syncing it later) is not yet a confirmed requirement. At minimum, the design must handle connectivity loss honestly and avoid silent data loss. The pilot discovery should determine whether true offline operation is essential.

### 8.3 Notifications

Candidate notifications include new pending QR orders, accepted/rejected customer requests, kitchen-ready items, and failed or delayed payment states. The delivery method (in-app, web push, local notification, audible alert, or another mechanism) depends on the chosen devices and implementation approach.

The system should not rely on a notification alone as the sole record of an order; users must also be able to find the order in the appropriate queue.

---

## 9. Non-Functional Requirements

These are proposed product-quality targets. Quantified service-level objectives should be set only after understanding the pilot's connectivity, workload, and business expectations.

### 9.1 Reliability

- Avoid losing accepted orders or confirmed payments.
- Handle retries and duplicate submissions safely.
- Preserve order/payment auditability.
- Have a defined backup, restore, and incident-recovery process before production use.

### 9.2 Usability

- Waiters should be able to enter an order quickly with minimal navigation.
- Kitchen tickets should be readable from the normal working distance and should emphasize new or delayed work.
- Cashier totals and payment status should be obvious.
- Customer QR ordering should be usable on typical mobile browsers without installing an app.
- Error messages should explain what happened and what the user can do next.

### 9.3 Security and privacy

- Enforce authentication for staff and authorization on every protected action.
- Give customer-facing pages access only to the information needed for the current ordering flow.
- Protect administrative and financial actions with appropriate permissions.
- Keep secrets and payment integration credentials out of client applications.
- Keep audit records for meaningful changes to orders, bills, payments, refunds, permissions, and stock.
- Define how long operational, financial, and customer data is retained, based on actual legal and business requirements.

### 9.4 Performance and responsiveness

- The menu, table view, pending-order queue, and kitchen tickets should remain usable during restaurant peak periods.
- Order and payment actions should provide clear feedback while processing.
- The system should avoid repeated manual refreshes if the selected architecture supports reliable real-time updates.
- Performance targets should be tested with a realistic pilot workload rather than guessed.

### 9.5 Maintainability and expansion

- Keep restaurant-specific configuration separate from the general product logic.
- Use a consistent permission model and shared order rules across interfaces.
- Avoid hardcoding the pilot restaurant's menu, prices, tax settings, tables, or staff.
- Design a reasonable path to serve additional restaurants later, while avoiding premature commitment to microservices, complex infrastructure, or multi-tenant hosting before the need is proven.

---

## 10. Proposed Delivery Stages

The product vision is complete management, but trying to launch every feature at once would increase risk. The following is a **proposed sequence**, to be refined after discovery.

### Stage 1 — Requirements discovery and workflow validation

- Observe the pilot restaurant's current process from seating to payment and closing a table.
- Document menu, customizations, table layout, staff roles, bill format, payment methods, and daily reporting requirements.
- Determine actual devices, internet reliability, and kitchen setup.
- Establish a baseline for order time, order errors, kitchen delays, and payment discrepancies.
- Confirm applicable tax/invoice rules and the preferred online payment provider.

**Exit condition:** The pilot workflows and key exceptions are documented and approved by the restaurant representative.

### Stage 2 — Core operational product

Proposed initial features:

- Staff login and role-based interfaces.
- Configurable tables and menu.
- Waiter-created dine-in orders.
- QR menu and QR order submission.
- Pending QR order queue and staff acceptance/rejection.
- Kitchen ticket/status workflow.
- Basic billing and cashier payment recording.
- Essential daily sales and activity reports.
- Audit history for important operational actions.

**Exit condition:** Staff can complete normal and exception-based dine-in workflows in a controlled test without losing or duplicating orders.

### Stage 3 — Online payment and production hardening

- Integrate and verify the chosen online payment provider.
- Handle delayed, failed, repeated, and refunded payment events.
- Reconcile gateway transactions with the application's records.
- Test security permissions, backup/restore, device loss, network interruptions, and recovery procedures.
- Finalize the point at which online payment becomes available.

**Exit condition:** Both online and cashier payment workflows can be reconciled and tested without false payment confirmations or double-recorded transactions.

### Stage 4 — Inventory and purchasing

- Add ingredient/stock-item records and units.
- Add suppliers and purchases as needed.
- Add stock-in, stock-out, stock counts, adjustments, and waste records.
- Define recipes and expected ingredient consumption.
- Add low-stock and stock discrepancy reporting.
- Agree on when inventory is reduced by an order and how cancellations, waste, and returns are handled.

**Exit condition:** Inventory movement can be explained and reconciled against purchases, sales, adjustments, and counts in the pilot.

### Stage 5 — Pilot operation and refinement

- Train the restaurant team and provide a simple operating guide.
- Run the product in real operating conditions with an agreed fallback process.
- Track incidents, staff feedback, order acceptance delays, order errors, payment discrepancies, and usage.
- Fix high-severity issues before adding nonessential features.
- Compare metrics to the baseline captured in Stage 1.

**Exit condition:** The product meets agreed reliability and usability expectations for the pilot and the restaurant is willing to continue using it.

### Stage 6 — Prepare for repeatable commercial sales

- Identify which requirements generalize across restaurants and which are pilot-specific.
- Improve onboarding, configuration, support, data backup, and account/restaurant provisioning.
- Create a repeatable installation or hosted deployment process.
- Decide pricing, support responsibilities, product update policy, and payment provider strategy.
- Validate with a second restaurant before assuming the pilot's workflows fit every restaurant.

**Exit condition:** A second restaurant can be configured without a separate codebase or extensive one-off changes.

---

## 11. Pilot Success Metrics

Capture baseline values before the pilot, then measure the same things during operation. Targets should be agreed with the restaurant rather than chosen arbitrarily.

| Area | Candidate measure | Why it matters |
|---|---|---|
| Order entry | Time to create and submit an order | Measures front-of-house efficiency |
| Order correctness | Missing, duplicated, or incorrect orders | Measures operational reliability |
| QR order review | Time from customer submission to staff decision | Detects approval-queue bottlenecks |
| Kitchen workflow | Time from acceptance to ready status | Provides visibility into preparation delays |
| Billing | Bill corrections and payment discrepancies | Measures financial accuracy |
| Online payments | Failed, pending, duplicate, or unreconciled transactions | Measures payment reliability |
| Inventory | Stock discrepancies and recorded wastage | Tests whether stock data is trustworthy |
| Staff adoption | Frequency of successful use and staff-reported problems | Shows whether the workflow is practical |
| Owner visibility | Ability to reconcile sales and payments at closing | Tests the business value of reporting |

The pilot should not be considered successful merely because the application runs. It should reliably support the restaurant's actual daily workflow and produce trustworthy records.

---

## 12. Risks and Mitigations

| Risk | Potential impact | Proposed response |
|---|---|---|
| Too many features in the first release | Delayed launch and a larger testing burden | Deliver in stages and prioritize the core dine-in workflow |
| QR requests wait too long for approval | Poor customer experience and duplicated attempts | Use a visible pending queue, age indicators, and measure confirmation time |
| Duplicate order submissions | Duplicate food preparation and customer disputes | Use safe retry/idempotency behavior and clear submission feedback |
| Prices or availability change after cart creation | Incorrect expectation or bill | Validate current values on submission and define an approval process for changes |
| Staff alters a kitchen order without notifying the kitchen | Incorrect food preparation | Record amendments and send a clear update to the affected kitchen ticket |
| Online gateway confirms late or repeatedly | Incorrect payment state or duplicate records | Verify events server-side, process safely, and reconcile transactions |
| Customer pays online and also pays cashier | Overpayment | Show reliable payment state to cashier and define an overpayment/refund procedure |
| QR code is copied or used maliciously | Wrong-table requests or unwanted pending orders | Use table-specific references, limits, staff approval, and code invalidation |
| Inventory records do not reflect reality | Poor purchasing decisions and false cost reports | Validate recipes/units and support counts, waste, and adjustments |
| Pilot-specific assumptions are hardcoded | Difficult expansion to other restaurants | Make business data configurable and test with a second restaurant |
| Connectivity fails during service | Interrupted workflow or uncertain submission state | Provide clear failure states, safe recovery, and decide whether offline mode is essential |

---

## 13. Commercial Strategy

### 13.1 Pilot first, then generalize

The first restaurant should help validate the workflows and reveal what customers actually need. Its requests should not automatically become universal product requirements.

For each customization request, decide whether it is:

1. A common requirement suitable for the standard product.
2. A configurable behavior useful to a class of restaurants.
3. A one-off request whose implementation and maintenance costs may not be worthwhile.

### 13.2 Expansion readiness

The initial release does not need every feature of a multi-tenant SaaS platform. Nevertheless, restaurant-specific configuration should be kept separate from core product logic, and access boundaries should be designed so that serving additional restaurants does not require a total rewrite.

Before selling broadly, validate with more than one restaurant. One pilot cannot prove that all restaurants have the same table workflow, kitchen layout, tax rules, devices, or payment preferences.

### 13.3 Commercial topics still to decide

- One-time license, subscription, installation fee, support fee, or a combination.
- Hosted service versus customer-managed deployment.
- Who provides device setup, training, backups, support, and updates.
- Which features are included in the base plan and which, if any, are add-ons.
- Payment gateway availability, merchant onboarding, and transaction costs.
- Data ownership, export, retention, and account termination policies.

No pricing or hosting model has been selected yet.

---

## 14. Architecture Decisions — Deliberately Deferred

No programming language, framework, database, hosting provider, or detailed deployment architecture has been selected in this planning phase.

Before making those decisions, clarify:

- Staff and customer device types.
- Expected number of simultaneous staff users and peak order volume.
- Internet reliability and offline requirements.
- Need for real-time kitchen updates and notifications.
- Payment gateway and required integrations.
- Receipt/kitchen printing and peripheral requirements.
- Hosting, backup, recovery, security, and ongoing support responsibilities.
- Whether the first deployment must be local to the restaurant, cloud-hosted, or support a hybrid approach.

The design should prioritize a coherent, maintainable application for the pilot. Microservices, Kubernetes, and other advanced infrastructure should be considered only when operational needs justify their complexity.

---

## 15. Open Decisions Register

These questions should be resolved through discussion or pilot discovery. Their current state is intentionally not presented as settled.

| Priority | Question | Why it matters |
|---|---|---|
| High | What devices does the pilot already have for waiters, kitchen, and cashier? | Determines the interface and hardware strategy |
| High | Should staff use one responsive/PWA application or native apps? | Affects deployment, maintenance, notifications, and device integration |
| High | When can a customer pay online: after staff accepts the order, when the bill is requested, or another time? | Defines checkout, cancellation, and refund behavior |
| High | Which online payment methods and gateway are available to the pilot? | Determines payment integration and reconciliation requirements |
| High | What tax, invoice, receipt, and service-charge rules apply? | Needed for correct billing and compliance |
| High | Is true offline operation required, or is safe handling of temporary connectivity loss sufficient? | Affects data synchronization and system complexity |
| High | Who may accept/reject QR orders and authorize cancellations, discounts, refunds, or bill edits? | Defines role permissions and accountability |
| Medium | Should customers confirm proposed item substitutions or changed totals? | Prevents surprise charges and disputes |
| Medium | Does the restaurant need split bills or multiple payment methods on one bill? | Increases billing and reconciliation complexity |
| Medium | What is the actual table count, staffing model, daily order volume, and peak period? | Helps scope and test the pilot realistically |
| Medium | Are kitchen stations separate for drinks, starters, and main courses? | Determines ticket routing and preparation workflow |
| Medium | When should inventory be reduced, and how should waste/cancellations be recorded? | Essential for reliable stock tracking |
| Medium | Are reservations, table merging/transfers, or a waitlist needed? | May affect table and dining-session modeling |
| Medium | Does the customer website need multiple languages or customer identifiers? | Affects usability, privacy, and localization |
| Later | What is the long-term pricing and hosting model? | Needed before repeatable commercial rollout |
| Later | Which features belong in the standard product versus paid add-ons? | Helps establish sustainable packaging and support |

---

## 16. Current Agreement Summary

The following items represent our current shared direction:

- Build a **commercial restaurant management system**.
- Start with **one small-to-medium family restaurant** as the pilot.
- Focus initially on **dine-in service**.
- Aim for **complete restaurant management**, including orders, kitchen operations, billing, payments, staff permissions, inventory, and reports, delivered in stages.
- Plan to sell the reusable product to other restaurants after the pilot; do not build a separate one-off codebase as the long-term strategy.
- Provide role-appropriate experiences for waiters, kitchen staff, cashiers, managers, and customers.
- Provide a **customer-facing QR website** so customers can browse the menu and submit orders without installing an app.
- Require **staff confirmation before a QR order enters the active kitchen workflow**.
- Support **both online payment and payment at the cashier**.
- Keep order state and payment state separate, verify online payments through a trusted backend/gateway mechanism, and preserve important audit history.
- Make restaurant-specific settings configurable and prepare a path to expansion without prematurely committing to complex infrastructure.
- Continue planning and validating requirements before writing code or selecting a stack.

### Immediate next step

Conduct requirements discovery with the pilot restaurant: map the current workflow from seating through order, kitchen, bill, payment, and table closure; identify staff permissions and exceptions; inspect available devices and connectivity; and record the menu, payment, and invoice requirements. Resolve the high-priority open decisions before turning this plan into a finalized MVP specification.
