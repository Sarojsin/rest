# Inventory & Procurement Module — Implementation Plan

**Owner:** restaurant-owner workflow  
**Status:** proposed (awaiting verification before build)  
**Location:** `backend/plan/Inventory_Procurement_plan.md`

---

## 1. Executive summary

Extend the existing restaurant inventory system into a full **Inventory & Procurement** section. Phase 1 adds unit conversion, cost per unit, purchases (multi-line with bill photos), supplier purchase history, recipe costing, and a proper stock movement ledger. Phase 2 connects inventory to the kitchen order flow (deduction on prep start with idempotent reversal on cancel). Phase 3 adds stock counts, batch/expiry tracking, and branch transfers.

**Key rule:** never write `Ingredient.current_stock` without a corresponding `StockMovement` row.  
**Key rule:** inventory deduction from orders happens exactly once per ticket — idempotent, atomic, reversed on void/cancel — never on every status change.

---

## 2. Current state (verified against codebase)

### What exists (backend: `backend/app/modules/inventory/`, frontend: `apps/web/src/pages/staff/InventoryPage.tsx`)

| Area | Backend state | Frontend state |
|------|---------------|----------------|
| Ingredients | `ingredients` table: name, code (unique per restaurant), unit, current_stock (int), minimum_stock, status (derived), supplier_id FK | Name, code, unit, current_stock, minimum_stock, supplier dropdown |
| Suppliers | `suppliers` table: name, contact_name, phone, email, address, city, state, postal_code, country, tax_id, is_active, rating, avg_delivery_days, notes | Name, contact_name, email, phone only |
| Purchase orders | `purchase_orders` + `purchase_order_items` (up to 50 lines per PO), status DRAFT/SUBMITTED/RECEIVED/CANCELLED, total_minor, received_date, receive flow writes RECEIVE movement | PO code, supplier, **one ingredient line only**, receive button |
| Recipes | `recipe_ingredients`: menu_item_id FK, ingredient_id, quantity_per_serving, quantity_per_order; `/recipes/{id}/cost` returns 0 (no cost_per_unit column) | Recipe builder: pick menu item, ingredient + quantity_per_serving rows |
| Stock movements | `stock_movements`: movement_type RECEIVE/ADJUST/DEDUCT/WASTE, signed quantity, new_balance, reason, reference_id → purchase_orders, reference_type, recorded_by_membership_id | Ingredient, movement_type, quantity, reason |
| Order-to-inventory | **None.** No auto-deduction on order placement or kitchen prep. | N/A |

### Gaps vs target spec

1. **Integers only** — cannot buy 10 kg and consume 250 g. Decimal / canonical base unit required.
2. **No ingredient cost per unit** — recipe cost always returns 0.
3. **Single-line PO form** — backend supports multi-line, UI does not.
4. **No bill photo attachment** on purchases.
5. **No supplier purchase history / total spend** view.
6. **Inventory not linked to orders** — consumption from recipes unimplemented.
7. **Single inventory page** — no dedicated routes/tabs per sub-module.

---

## 3. Design principles

1. **Ledger-first.** `StockMovement` is the authoritative log. `Ingredient.current_stock` is a denormalized cache updated inside the same transaction as every movement row.
2. **Canonical base units.** Every ingredient has a `base_unit` (grams / ml / pieces) and optional conversion ratios to common units (kg, litre, all-purpose). Quantities stored in base unit internally; display converts for UI.
3. **Idempotent consumption.** Auto-deduction keyed by ticket/order id; a second deduction for the same ticket is a no-op.
4. **One consumption policy.** Deduct when kitchen ticket enters preparation (`IN_PROGRESS`), not on order create or status change. Reversal on void/cancel only if a deduction exists.
5. **No silent deletes.** Corrections recorded as new movements; purchase records never hard-deleted after receipt.
6. **Restaurant-scoped.** Phase 1 keeps all inventory at restaurant level (no `branch_id`). Branch transfers deferred to phase 3 unless product requires day one.

---

## 4. Scope phases

### Phase 1 — Core inventory & procurement (weeks 1–2)

**A. Ingredients schema upgrade**
- Add `cost_per_unit_minor: int` (NPR minor units, e.g. paisa)
- Add `base_unit: str` default `"pieces"`; category: meat/veg/dairy/spices/other
- Add `unit_conversions` JSON column (unit → multiplier relative to base unit, e.g. `{"kg": 1000, "g": 1}`)
- Add `storage_location: str` (freezer/refrigerator/dry storage)
- Add `sku: str` unique per restaurant (required, indexed)
- Existing `code` stays as alias/internal code
- Decimal migration: `current_stock`, movement `quantity`, recipe quantities become `numeric` (or integer in base-unit subunits like grams). Decision: **store as integer subunits (grams/ml/pieces)** to avoid float errors; expose decimals in UI.
- Status recomputed: IN_STOCK / LOW_STOCK (≤ min) / OUT_OF_STOCK (= 0)

**B. Purchases (rename Purchase Orders)**
- Multi-line purchase form (already supported by backend `purchase_order_items`)
- Add `bill_photo_urls: text[]` or separate attachment table + max 3 photos per purchase
- Add purchase date (default now), supplier or "walk-in supplier" toggle
- Auto-calculated total
- Receive flow unchanged (adds to stock, writes RECEIVE movement)
- Prevent delete after received; cancel allowed only in DRAFT/SUBMITTED

**C. Stock movements ledger UI**
- Ledger table with columns: date/time, who (membership name), movement type, previous qty, new qty, reason, reference (PO # / order # / manual)
- Filter by ingredient, date range, movement type
- Low-stock list (ingredients at/below minimum_stock)

**D. Recipe costing**
- `cost_per_unit_minor` on Ingredient makes `/recipes/{menu_item_id}/cost` return real values
- Compute cost per serving / per order from recipe quantities × unit costs
- Expose margin hint (selling price − ingredient cost)

**E. Suppliers**
- Expose remaining backend fields in UI (address, tax_id, rating, notes)
- Supplier detail page: total purchases to date, purchase history list, document attachment (optional)

**F. Frontend shell**
- Split `InventoryPage.tsx` into sidebar section **Inventory & Procurement**:
  - Inventory Overview
  - Ingredients
  - Stock Movements
  - Stock Counts (placeholder page, phase 3 backend)
  - Recipes
  - Suppliers
  - Purchase Orders
  - Storage Locations (label field on ingredient; standalone page phase 3)
  - Waste Management (filter movements by WASTE; standalone page phase 3)
  - Inventory Reports (placeholder page, phase 3)

### Phase 2 — Order-driven consumption (weeks 3–4)

**A. Consumption service** (`services/inventory_consumption.py`)
- Trigger: kitchen ticket status → `IN_PROGRESS` (preparation starts)
- Look up `RecipeIngredient` rows for each order line menu item
- Deduct `quantity_per_order × order_qty` in base-unit subunits from each ingredient
- Atomic per ticket; idempotency key `deduct:ticket:{ticket_id}`
- If any ingredient would go negative → still allow, record movement anyway, flag `SHORTAGE` on ticket/order for manager review
- Write `StockMovement` type DEDUCT, reference_type ORDER, reference_id = ticket id

**B. Reversal**
- Ticket cancelled / voided → if deduction exists, write REVERSAL movement restoring qty, keyed `reversal:ticket:{ticket_id}`

**C. Hook**
- Wire into kitchen flow where ticket moves to IN_PROGRESS (operations module). No change to customer-facing order submission.

### Phase 3 — Advanced inventory (weeks 5–6)

- **Stock counts:** blind count entry, variance adjustment movements
- **Batch & expiry tracking:** `ingredient_batches` rows (batch no, expiry date, qty, cost); movements reference batch; FEFO picking
- **Branch transfers:** `branch_id` on ingredients/movements; Transfer In / Transfer Out movement types
- **Storage locations:** dedicated page, per-ingredient default location
- **Waste management:** dedicated page listing WASTE movements with reason categories
- **Inventory reports:** consumption by ingredient, purchase spend by supplier, margin by menu item, low-stock report

---

## 5. Data model changes (backend)

All changes in `backend/app/modules/inventory/models.py` unless noted.

### 5.1 `ingredients` — add columns

| Column | Type | Notes |
|--------|------|-------|
| `sku` | String, unique per restaurant | Required, indexed |
| `category` | String | meat/veg/dairy/spices/other |
| `base_unit` | String | grams/ml/pieces |
| `unit_conversions` | JSON | e.g. `{"kg": 1000, "g": 1}` |
| `cost_per_unit_minor` | Integer | NPR paisa, default 0 |
| `storage_location` | String | freezer/refrigerator/dry storage/other |

### 5.2 Decimal / subunit strategy

- `Ingredient.current_stock`: change to `Numeric` (or keep integer but interpret as base-unit subunits — **recommended**)
- `StockMovement.quantity`: signed numeric / integer subunits
- `StockMovement.new_balance`: numeric / integer subunits
- `RecipeIngredient.quantity_per_serving` / `quantity_per_order`: numeric / integer subunits
- UI accepts decimals (e.g. 2.5 kg) and converts to subunits using `unit_conversions`

### 5.3 `purchase_orders` — add columns

| Column | Type | Notes |
|--------|------|-------|
| `purchase_date` | Date | default today |
| `bill_photo_urls` | text[] | up to 3 URLs |
| `supplier_is_walk_in` | Boolean | default false |

### 5.4 `suppliers` — no schema change (backend already has fields)

UI exposes remaining fields; add `total_purchases_minor` computed column or query aggregation.

### 5.5 `stock_movements` — optional additions

| Column | Type | Notes |
|--------|------|-------|
| `idempotency_key` | String, indexed | `deduct:ticket:{id}` etc. |
| `batch_id` | FK → ingredient_batches | phase 3 |
| `previous_balance` | numeric | snapshot before movement |

---

## 6. Endpoint changes

All under `/api/v1/inventory` (existing router `backend/app/modules/inventory/router.py`).

### 6.1 Ingredients
- `GET /ingredients` — add `?sku`, `?category`, `?storage_location` filters; return cost_per_unit_minor, base_unit, conversions
- `POST /ingredients` — require sku; validate conversions JSON
- `PATCH /ingredients/{id}` — allow cost_per_unit_minor, storage_location updates; re-derive status
- `PATCH /ingredients/{id}/stock` — keep absolute set, log ADJUST movement with idempotency key `adjust:manual:{id}` if not provided

### 6.2 Purchase orders
- `POST /purchase-orders` — multi-line items array (already backend-supported), purchase_date, bill_photo_urls, walk-in flag
- `GET /purchase-orders` — add `?date_from`, `?date_to`, `?supplier_id`, `?status`
- `POST /purchase-orders/{id}/receive` — unchanged logic; validate not already received

### 6.3 Stock movements
- `GET /stock-movements` — add `?idempotency_key`, `?reference_type`, `?reference_id`; expose previous_balance
- `POST /stock-movements` — require idempotency_key for DEDUCT/WASTE/REVERSAL types; reject duplicate key

### 6.4 Recipes
- `PUT /recipes/{menu_item_id}` — full replace (unchanged); validate ingredients exist and belong to restaurant
- `GET /recipes/{menu_item_id}/cost` — return real cost now (uses cost_per_unit_minor)

### 6.5 New: consumption
- `POST /inventory/consume/ticket/{ticket_id}` — manual trigger for phase 2 testing (idempotent)
- `GET /inventory/shortages` — list tickets/orders with shortage flags

---

## 7. Consumption policy — detailed behavior (phase 2)

| Event | Action | Idempotency key |
|-------|--------|-----------------|
| Kitchen ticket → IN_PROGRESS | For each line item, deduct recipe qty × qty from ingredients | `deduct:ticket:{ticket_id}` |
| Ticket cancelled/voided after deduction | REVERSAL movement restoring qty | `reversal:ticket:{ticket_id}` |
| Manual waste/adjust | ADJUST / WASTE movement | `adjust:manual:{id}` / `waste:manual:{id}` |
| PO receive | RECEIVE movement | `receive:po:{po_id}` |

**Shortage handling:** do not block kitchen. Record `shortage=true` on ticket context; manager sees low-stock/reorder report.

**Idempotency:** before writing any movement, check `idempotency_key` uniqueness; if exists, return cached result without new row.

---

## 8. Frontend changes

### 8.1 Routes (`apps/web/src/App.tsx`)
Add sidebar section **Inventory & Procurement** with routes:
- `/inventory` → Overview (current single page simplified to dashboard cards)
- `/inventory/ingredients` → full ingredient table + form
- `/inventory/movements` → ledger table + filters
- `/inventory/recipes` → recipe builder + cost view
- `/inventory/suppliers` → supplier table + detail/history
- `/inventory/purchases` → multi-line purchase form + receive
- `/inventory/counts` → placeholder (phase 3)
- `/inventory/waste` → WASTE movement list (phase 2+)
- `/inventory/reports` → placeholder (phase 3)

### 8.2 Component changes
- `IngredientForm`: sku, name, category, base_unit, unit conversions (dynamic rows), cost_per_unit_minor, storage_location, min stock, supplier
- `PurchaseForm`: supplier (or walk-in toggle), date, dynamic ingredient lines (ingredient, qty, unit, unit price), bill photo uploads, total auto-calc
- `MovementLedger`: table with all movement columns, export-friendly
- `RecipeCost`: per menu item, ingredient cost breakdown, margin vs selling price

### 8.3 Permissions
Existing permissions `inventory.read` / `inventory.manage` cover all endpoints. No new permission needed for phase 1-2.

---

## 9. Migration steps (backend)

1. Create Alembic revision adding columns to `ingredients`, `purchase_orders`
2. Change numeric columns from `Integer` to `Numeric`/`BigInteger` (subunit strategy decision first)
3. Backfill: existing `current_stock` integer values treated as base-unit subunits (pieces default)
4. Recompute ingredient status from new stock values
5. Add indexes: `sku`, `idempotency_key`, `reference_type + reference_id`

---

## 10. Risks & open decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Decimal storage | `Numeric` SQL type vs integer subunits (grams/ml/pieces) | **Integer subunits** — avoids float rounding, simpler indexing |
| Branch scope | Restaurant-level vs branch-level stock | **Restaurant-level phase 1**; branch transfers phase 3 |
| Consumption trigger | Ticket IN_PROGRESS vs order completed | **IN_PROGRESS** — matches physical ingredient use |
| PO vs Purchase naming | Rename "Purchase Orders" → "Purchases" | **Rename in UI only**; keep backend table names |
| Bill photos | Attachment table vs text[] URLs | **text[] URLs** phase 1; attachment table phase 3 if needed |

---

## 11. Verification checklist (before build starts)

- [ ] Confirm current backend `Ingredient.current_stock` type and all write paths in `services/inventory.py`
- [ ] Confirm frontend `InventoryPage.tsx` current route guard and data fetching pattern
- [ ] Confirm Alembic is configured and last revision (`pa0018`) applies cleanly
- [ ] Confirm `recipe_ingredients.menu_item_id` FK points to `menu_items.id` and restaurant tenancy check exists
- [ ] Decide subunit storage strategy (grams vs Numeric)
- [ ] Decide branch scope (restaurant-level phase 1 confirmed?)

---

## 12. Immediate next step (phase 1, task 1)

Run Alembic migration adding `sku`, `category`, `base_unit`, `unit_conversions`, `cost_per_unit_minor`, `storage_location` to `ingredients`, plus `purchase_date`, `bill_photo_urls`, `supplier_is_walk_in` to `purchase_orders`, and `idempotency_key` to `stock_movements`.

Once verified, switch to build agent and start with the migration + ingredient schema upgrade.
