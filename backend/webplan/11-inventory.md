# Phase 11 — Inventory & Stock Management Plan

## Objective
Enable restaurant managers to track ingredients, raw materials, and stock levels with low-stock notifications, supplier tracking, and automatic ingredient deduction when orders are completed. This is a key differentiator for competing as a complete restaurant management SaaS.

## Scope
### Implemented (Foundation)
- Order model with COMPLETED status
- OrderItem with `item_name_snapshot`, `quantity`, `unit_price_minor`
- MenuItem model with `current_price_minor`, `status` (PUBLISHED/DRAFT)
- Kitchen ticket system with item-level status tracking
- `_tax_rate()` function reading `RestaurantSettings`
- `line_amounts()` utility computing subtotal, tax, total from price and quantity

### New / Planned

1. **Ingredient & Raw Material Management**
   - Create ingredient profiles with name, unit of measure (kg, gram, litre, pieces)
   - Define minimum stock levels per ingredient
   - Track current stock quantity per ingredient
   - Ingredient status: in-stock, low-stock, out-of-stock

2. **Supplier Management**
   - Supplier profiles: name, contact info, address, phone
   - Supplier payment terms (net-15, net-30, etc.)
   - Track outstanding supplier balances
   - Supplier performance (delivery time, quality ratings)

3. **Purchase Orders**
   - Create purchase orders linked to suppliers
   - Add items/quantities per purchase order
   - PO status: DRAFT → SUBMITTED → RECEIVED → CANCELLED
   - PO total and payment tracking

4. **Stock Receiving & Adjustments**
   - Record received stock against POs
   - Update ingredient stock quantities on receive
   - Stock adjustments: wastage, count corrections, complimentary items
   - Track adjustment reason and user

5. **Recipe & Automatic Deduction**
   - Link menu recipes to ingredients (e.g., "Burger" uses 1x bun, 1x patty, 0.2kg beef, 0.05kg cheese)
   - Configure deduction rules:
     - Deduct when order marked COMPLETED
     - Deduct when kitchen item marked READY
     - Deduct on a schedule (once per day at close)
   - Per-ingredient deduction amount or recipe-based calculation

6. **Low-Stock Notifications**
   - Alert when ingredient stock ≤ minimum threshold
   - Notification via system UI, optional email/Service Call
   - Suppress if already have open purchase order for ingredient
   - Dashboard widget: "Low Stock Alerts"

7. **Stock Movement History**
   - Log every stock change: receive, adjustment, deduction, wastage
   - Include: quantity before/after, reason, user, timestamp
   - Search/filter by ingredient, date range, reason type
   - Reports: total received, total wasted, total consumed per ingredient

8. **Inventory Reports**
   - Ingredient consumption report (per period)
   - Waste/wasage report
   - Supplier performance report (cost per unit, on-time delivery)
   - Stock value report (current stock × current purchase price)
   - Low-stock summary

## Technical Design

### New Models (to be created)
- `Ingredient` — name, unit, current_stock, minimum_stock, status, supplier_id (FK)
- `PurchaseOrder` — supplier_id, status, items (JSON or line items), total, expected_date, received_date, notes
- `StockMovement` — ingredient_id, change_quantity, new_balance, reason (RECEIVE/ADJUST/DEDUCT/WASTE), user_id, created_at
- `RecipeIngredient` — ingredient_id, menu_item_id, quantity_per_serving (or per order)

### Existing Models to Extend
- `MenuItem` — add `cost_minor` (food cost for recipe costing)
- `RestaurantSettings` — add inventory-related config (enable_auto_deduction, deduction_rule)

### API Endpoints (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/ingredients` | List ingredients with stock levels |
| `POST /api/v1/ingredients` | Create new ingredient |
| `GET /api/v1/ingredients/{id}` | Get ingredient detail |
| `PATCH /api/v1/ingredients/{id}` | Update stock level or minimum |
| `GET /api/v1/suppliers` | List suppliers |
| `POST /api/v1/suppliers` | Create supplier |
| `POST /api/v1/purchase-orders` | Create purchase order |
| `POST /api/v1/purchase-orders/{id}/receive` | Receive PO, update stock |
| `POST /api/v1/stock-adjustments` | Record stock adjustment |
| `GET /api/v1/inventory/reports/consumption` | Consumption report |
| `GET /api/v1/inventory/reports/waste` | Waste report |
| `GET /api/v1/inventory/reports/value` | Stock value report |

### Schemas (new)
- `IngredientOut` — id, name, unit, current_stock, minimum_stock, status, supplier_name
- `IngredientIn` — name, unit, minimum_stock, supplier_id (optional)
- `PurchaseOrderOut` — id, supplier, items, total, status, dates
- `PurchaseOrderItem` — ingredient_id, quantity, unit_price, total
- `StockMovementOut` — id, ingredient, change, new_balance, reason, user, timestamp
- `RecipeIngredientIn` — ingredient_id, quantity_per_serving

### Integration Points
- **Kitchen**: When ticket items marked READY, trigger ingredient deduction (if auto-deduction enabled)
- **Orders**: When order marked COMPLETED, trigger ingredient deduction (alternative flow)
- **Purchase Orders**: On receive, add `change_quantity` to ingredient `current_stock`
- **Dashboard**: Consumption + low-stock widgets
- **Audit**: All stock changes audited with `record_audit()`
- **Outbox**: Stock movement events for external sync (e.g., kitchen display, supplier portals)

### Configuration
- Per-restaurant ingredient enablement (not all restaurants need full inventory)
- Deduction rule configuration (when: COMPLETED, when: READY, both, or scheduled)
- Unit conversion support (if recipe uses grams but purchase is in kg)
- Price source: current MenuItem price vs historical purchase price

## Migration / Rollback
- New tables: `ingredients`, `purchase_orders`, `stock_movements`, `recipe_ingredients`
- Extend existing: `menu_items` (cost_minor), `restaurant_settings` (inventory config)
- Indexes on `ingredient_id`, `restaurant_id`, `created_at` for report performance
- Rollback: drop new tables, remove extended columns, revert API routes

## Acceptance Criteria
- [ ] Ingredient can be created with unit and minimum stock level
- [ ] Stock level updated on receive, adjustment, and deduction
- [ ] Auto-deduction triggered when order COMPLETED or kitchen item READY
- [ ] Low-stock notification generated when stock ≤ minimum
- [ ] Purchase order created, received, stock updated
- [ ] Stock movement logged with reason and user
- [ ] Consumption report shows ingredient usage per period
- [ ] Waste report lists all wastage entries with reasons
- [ ] All stock actions appear in audit trail
- [ ] 100% of integration tests pass with test DB

## Open Questions / Dependent Work
- Which payment gateway integrations are needed first? (affects billing priority)
- Should recipe linking be manual (manager enters) or import from menu setup?
- Notification channel: in-app only, or email/SMS too?
- Costing: use MenuItem.current_price_minor as cost, or separate purchase cost field?
- Integration with supplier portals for automated PO placement (future)

## Phase Order Relative to Other Work
- **Before**: Billing/POS (need revenue data to value inventory), Multi-branch (each branch independent inventory)
- **After**: Multi-branch (per-branch inventory), SaaS subscriptions (feature access control), Customer loyalty (linked purchase history)
- **Parallel potential**: Billing + Inventory (same order items feed both)