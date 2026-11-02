# Menu: Inheritance, Overrides, Draft & Publish

Resolves the biggest schema/workflow mismatch found in review: publish state exists in the **data model from M3**, not retrofitted.

## 1. Definition vs. override split

- **Tenant-level definitions** (`menu_categories`, `menu_items`, `menu_option_groups`, `menu_options`): name, description, images, default price, categories, options, dietary tags. `branch_id NULL` = tenant-wide; `branch_id SET` = branch-only item (exists in one branch only).
- **Branch-level state** (`menu_item_branch_overrides` — 03 §3): `is_available`, `is_hidden`, `price_override_minor`.
- Resolution to customer/kitchen: `branch_item = override.visible ? override : tenant_def` — the *merged public menu* for a branch = tenant defs (not hidden) joined to overrides (branch or default).

## 2. Inheritance rules (locked)

| Tenant-level edit | Propagation |
|---|---|
| description, options, images | all branches that did not locally override that field — branches that did keep theirs |
| default price | branches **without** `price_override_minor` follow immediately; overridden branches keep price (a branch-local price change is never silently overwritten) |
| item archived/hidden at tenant level | hidden everywhere (archived is final; availability flags stay for when it returns) |
| category reorder/rename | tenant-wide display, branches don't override order in pilot |

## 3. Draft & publish model (M3 columns)

```sql
ALTER TABLE menu_items
  ADD COLUMN draft_data JSONB,        -- staged edits while published def stays live
  ADD COLUMN published_at TIMESTAMPTZ,
  ADD COLUMN published_by_membership_id UUID REFERENCES memberships(id);
```

- Customer/kitchen read **published** fields only. Manage screen edits tenant item (live fields) → **Save as draft** stages into `draft_data` → **Publish** applies draft to live fields, sets `published_at`, emits `menu.published` outbox event → customer apps refetch.
- Per-branch changes (price/availability) are operational and take effect immediately (no draft) — availability is a real-time operational truth (sold-out salmon must be instant), while catalog content (descriptions/photos/prices) is drafted.
- Publish is permission-gated (`menu.publish`) and audited. Bulk publish validates the whole branch menu (no empty categories) before commit.
- Drafts survive incomplete sessions; discard option available.

## 4. Availability semantics

- `menu_item_branch_overrides.is_available` per branch; default TRUE for branches without a row.
- Staff toggles "sold out" from dashboard/kitchen — instant, real-time pushed (13), validated server-side at order submit and re-validated again at accept time (QR flow 12 §4).
- Availability never has a draft state.

## 5. Order-time price integrity

- Cart prices on customer app are estimates; at submit the server computes from published price + options; drift ⇒ `409 PRICE_CHANGED {item_id, old_minor, new_minor}` — client re-confirms; **never silently different price** (12 §4).
- Waiter orders: submit against live published price; amended orders snapshot prices at line creation.
- Bill lines are immutable snapshots (`bill_items` unchanged from current design).

## 6. Scheduled menus — deferred

Breakfast/lunch/dinner scheduling is out of pilot scope (`23` decisions register, "v2"). Schema note: `hours_config` JSONB on branches is reserved; scheduling needs a `menu_time_windows` table when built.
