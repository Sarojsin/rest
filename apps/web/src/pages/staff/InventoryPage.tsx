import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  apiFetch,
  formatMoney,
  type Ingredient,
  type MenuCategory,
  type PurchaseOrder,
  type RecipeIngredient,
  type StockMovement,
  type Supplier,
} from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

type IngredientDraft = {
  name: string;
  code: string;
  unit: string;
  current_stock: string;
  minimum_stock: string;
  supplier_id: string;
};

const EMPTY_INGREDIENT: IngredientDraft = {
  name: "",
  code: "",
  unit: "pieces",
  current_stock: "0",
  minimum_stock: "0",
  supplier_id: "",
};

type SupplierDraft = { name: string; contact_name: string; email: string; phone: string };
const EMPTY_SUPPLIER: SupplierDraft = { name: "", contact_name: "", email: "", phone: "" };

type RecipeDraftItem = { ingredient_id: string; quantity_per_serving: number };

export default function InventoryPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [recipes, setRecipes] = useState<RecipeIngredient[]>([]);
  const [menu, setMenu] = useState<MenuCategory[]>([]);

  const [ingredientDraft, setIngredientDraft] = useState<IngredientDraft>(EMPTY_INGREDIENT);
  const [supplierDraft, setSupplierDraft] = useState<SupplierDraft>(EMPTY_SUPPLIER);
  const [movementDraft, setMovementDraft] = useState({
    ingredient_id: "",
    movement_type: "RECEIVE",
    quantity: "1",
    reason: "",
  });
  const [poDraft, setPoDraft] = useState({
    code: "",
    supplier_id: "",
    ingredient_id: "",
    quantity: "1",
    unit_price_minor: "0",
  });
  const [recipeItem, setRecipeItem] = useState("");
  const [recipeMenuId, setRecipeMenuId] = useState("");
  const [recipeDraft, setRecipeDraft] = useState<RecipeDraftItem[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const menuItems = useMemo(
    () => menu.flatMap((category) => category.items.map((item) => ({ ...item, category: category.name }))),
    [menu]
  );

  const load = useCallback(async () => {
    const [ingredientList, supplierList, orderList, movementList, recipeList, menuList] =
      await Promise.all([
        apiFetch<Ingredient[]>("/api/v1/inventory/ingredients"),
        apiFetch<Supplier[]>("/api/v1/inventory/suppliers"),
        apiFetch<PurchaseOrder[]>("/api/v1/inventory/purchase-orders"),
        apiFetch<StockMovement[]>("/api/v1/inventory/stock-movements"),
        apiFetch<RecipeIngredient[]>("/api/v1/inventory/recipes"),
        apiFetch<MenuCategory[]>("/api/v1/menu"),
      ]);
    setIngredients(ingredientList);
    setSuppliers(supplierList);
    setOrders(orderList);
    setMovements(movementList);
    setRecipes(recipeList);
    setMenu(menuList);
  }, []);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof ApiError ? err.detail : "Could not load inventory.")
    );
  }, [load]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The inventory action failed.");
    } finally {
      setBusy(false);
    }
  }

  function createIngredient() {
    return run(async () => {
      await apiFetch<Ingredient>("/api/v1/inventory/ingredients", {
        method: "POST",
        body: JSON.stringify({
          name: ingredientDraft.name.trim(),
          code: ingredientDraft.code.trim() || null,
          unit: ingredientDraft.unit.trim() || "pieces",
          current_stock: Number(ingredientDraft.current_stock) || 0,
          minimum_stock: Number(ingredientDraft.minimum_stock) || 0,
          supplier_id: ingredientDraft.supplier_id || null,
        }),
      });
      setIngredientDraft(EMPTY_INGREDIENT);
      return "Ingredient added.";
    });
  }

  function createSupplier() {
    return run(async () => {
      await apiFetch<Supplier>("/api/v1/inventory/suppliers", {
        method: "POST",
        body: JSON.stringify({
          name: supplierDraft.name.trim(),
          contact_name: supplierDraft.contact_name.trim() || null,
          email: supplierDraft.email.trim() || null,
          phone: supplierDraft.phone.trim() || null,
        }),
      });
      setSupplierDraft(EMPTY_SUPPLIER);
      return "Supplier added.";
    });
  }

  function recordMovement() {
    return run(async () => {
      const quantity = Number(movementDraft.quantity);
      await apiFetch<StockMovement>("/api/v1/inventory/stock-movements", {
        method: "POST",
        body: JSON.stringify({
          ingredient_id: movementDraft.ingredient_id,
          movement_type: movementDraft.movement_type,
          quantity,
          reason: movementDraft.reason.trim() || null,
        }),
      });
      setMovementDraft({ ...movementDraft, quantity: "1", reason: "" });
      return "Stock movement recorded.";
    });
  }

  function createPurchaseOrder() {
    return run(async () => {
      await apiFetch<PurchaseOrder>("/api/v1/inventory/purchase-orders", {
        method: "POST",
        body: JSON.stringify({
          code: poDraft.code.trim(),
          supplier_id: poDraft.supplier_id,
          items: [
            {
              ingredient_id: poDraft.ingredient_id,
              quantity: Number(poDraft.quantity) || 1,
              unit_price_minor: Number(poDraft.unit_price_minor) || 0,
            },
          ],
        }),
      });
      setPoDraft({ ...poDraft, code: "", quantity: "1", unit_price_minor: "0" });
      return "Purchase order created.";
    });
  }

  function receive(order: PurchaseOrder) {
    return run(async () => {
      await apiFetch<PurchaseOrder>(`/api/v1/inventory/purchase-orders/${order.id}/receive`, {
        method: "POST",
      });
      return `Purchase order ${order.code} received into stock.`;
    });
  }

  function addRecipeItem() {
    if (!recipeItem) return;
    const existing = recipeDraft.find((entry) => entry.ingredient_id === recipeItem);
    if (existing) {
      setRecipeDraft(
        recipeDraft.map((entry) =>
          entry.ingredient_id === recipeItem
            ? { ...entry, quantity_per_serving: entry.quantity_per_serving + 1 }
            : entry
        )
      );
    } else {
      setRecipeDraft([...recipeDraft, { ingredient_id: recipeItem, quantity_per_serving: 1 }]);
    }
    setRecipeItem("");
  }

  function saveRecipe() {
    if (!recipeMenuId) return Promise.resolve();
    return run(async () => {
      await apiFetch<RecipeIngredient[]>(`/api/v1/inventory/recipes/${recipeMenuId}`, {
        method: "PUT",
        body: JSON.stringify({ items: recipeDraft }),
      });
      setRecipeDraft([]);
      return "Recipe saved.";
    });
  }

  const selectedRecipes = recipes.filter((row) => row.menu_item_id === recipeMenuId);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Inventory"
        title="Stock, suppliers & recipes"
        sub="Stock levels move only through recorded movements or received purchase orders, so every change leaves an audit trail."
        actions={
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <section className="section-card" aria-labelledby="ingredients-title">
        <div className="section-card-head">
          <h3 id="ingredients-title">Ingredients</h3>
          <span className="muted text-sm">{ingredients.length} tracked</span>
        </div>
        <div className="section-card-body">
          {ingredients.length === 0 ? <p className="muted">No ingredients yet.</p> : null}
          {ingredients.map((ingredient) => (
            <div className="list-row" key={ingredient.id}>
              <span>
                <strong>{ingredient.name}</strong>
                <span className="muted text-sm">
                  {" "}
                  · {ingredient.current_stock} {ingredient.unit} (min {ingredient.minimum_stock})
                </span>
              </span>
              <span
                className={`badge ${
                  ingredient.status === "IN_STOCK"
                    ? "new"
                    : ingredient.status === "LOW_STOCK"
                      ? "pending"
                      : "rejected"
                }`}
              >
                {ingredient.status.replace("_", " ")}
              </span>
            </div>
          ))}

          {canManage ? (
            <form
              className="stack"
              style={{ marginTop: "var(--space-4)" }}
              onSubmit={(event) => {
                event.preventDefault();
                void createIngredient();
              }}
            >
            <h4 style={{ margin: 0 }}>Add ingredient</h4>
            <div className="grid two">
              <label className="field">
                Name
                <input
                  value={ingredientDraft.name}
                  onChange={(event) =>
                    setIngredientDraft({ ...ingredientDraft, name: event.target.value })
                  }
                  required
                />
              </label>
              <label className="field">
                Unit
                <input
                  value={ingredientDraft.unit}
                  onChange={(event) =>
                    setIngredientDraft({ ...ingredientDraft, unit: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Current stock
                <input
                  type="number"
                  min={0}
                  value={ingredientDraft.current_stock}
                  onChange={(event) =>
                    setIngredientDraft({ ...ingredientDraft, current_stock: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Minimum stock
                <input
                  type="number"
                  min={0}
                  value={ingredientDraft.minimum_stock}
                  onChange={(event) =>
                    setIngredientDraft({ ...ingredientDraft, minimum_stock: event.target.value })
                  }
                />
              </label>
            </div>
            <label className="field">
              Supplier
              <select
                value={ingredientDraft.supplier_id}
                onChange={(event) =>
                  setIngredientDraft({ ...ingredientDraft, supplier_id: event.target.value })
                }
              >
                <option value="">No supplier</option>
                {suppliers.map((supplier) => (
                  <option key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn" type="submit" disabled={busy || !ingredientDraft.name.trim()}>
              Add ingredient
            </button>
            </form>
          ) : null}
        </div>
      </section>

      <section className="section-card" aria-labelledby="movements-title">
        <div className="section-card-head">
          <h3 id="movements-title">Record a stock movement</h3>
        </div>
        <div className="section-card-body">
          {canManage ? (
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void recordMovement();
              }}
            >
            <div className="grid two">
              <label className="field">
                Ingredient
                <select
                  value={movementDraft.ingredient_id}
                  onChange={(event) =>
                    setMovementDraft({ ...movementDraft, ingredient_id: event.target.value })
                  }
                  required
                >
                  <option value="">Select…</option>
                  {ingredients.map((ingredient) => (
                    <option key={ingredient.id} value={ingredient.id}>
                      {ingredient.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Type
                <select
                  value={movementDraft.movement_type}
                  onChange={(event) =>
                    setMovementDraft({ ...movementDraft, movement_type: event.target.value })
                  }
                >
                  <option value="RECEIVE">Receive</option>
                  <option value="DEDUCT">Deduct</option>
                  <option value="WASTE">Waste</option>
                  <option value="ADJUST">Adjust (signed)</option>
                </select>
              </label>
              <label className="field">
                Quantity
                <input
                  type="number"
                  value={movementDraft.quantity}
                  onChange={(event) =>
                    setMovementDraft({ ...movementDraft, quantity: event.target.value })
                  }
                  required
                />
              </label>
              <label className="field">
                Reason
                <input
                  value={movementDraft.reason}
                  onChange={(event) =>
                    setMovementDraft({ ...movementDraft, reason: event.target.value })
                  }
                  placeholder="Delivery, spoilage, count correction…"
                />
              </label>
            </div>
            <button className="btn" type="submit" disabled={busy || !movementDraft.ingredient_id}>
              Record movement
            </button>
            </form>
          ) : null}

          {movements.length > 0 ? (
            <div style={{ marginTop: "var(--space-3)" }}>
              {movements.slice(0, 12).map((movement) => {
                const ingredient = ingredients.find((entry) => entry.id === movement.ingredient_id);
                return (
                  <div className="audit-row" key={movement.id}>
                    <div>
                      <span className="audit-action">{movement.movement_type}</span>
                      <div>
                        {ingredient?.name ?? movement.ingredient_id.slice(0, 8)} ·{" "}
                        {movement.quantity > 0 ? "+" : ""}
                        {movement.quantity} → {movement.new_balance}
                      </div>
                    </div>
                    <time className="muted text-sm" dateTime={movement.created_at}>
                      {new Date(movement.created_at).toLocaleString()}
                    </time>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      </section>

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="suppliers-title">
          <div className="section-card-head">
            <h3 id="suppliers-title">Suppliers</h3>
            <span className="muted text-sm">{suppliers.length} active</span>
          </div>
          <div className="section-card-body">
            {suppliers.map((supplier) => (
              <div className="list-row" key={supplier.id}>
                <span>
                  <strong>{supplier.name}</strong>
                  {supplier.contact_name ? (
                    <span className="muted text-sm"> · {supplier.contact_name}</span>
                  ) : null}
                </span>
                <span className="muted text-sm">{supplier.email || supplier.phone || "—"}</span>
              </div>
            ))}
            {canManage ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-3)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void createSupplier();
                }}
              >
              <label className="field">
                Name
                <input
                  value={supplierDraft.name}
                  onChange={(event) => setSupplierDraft({ ...supplierDraft, name: event.target.value })}
                  required
                />
              </label>
              <div className="grid two">
                <label className="field">
                  Contact
                  <input
                    value={supplierDraft.contact_name}
                    onChange={(event) =>
                      setSupplierDraft({ ...supplierDraft, contact_name: event.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Email
                  <input
                    type="email"
                    value={supplierDraft.email}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, email: event.target.value })}
                  />
                </label>
              </div>
              <button className="btn secondary" type="submit" disabled={busy || !supplierDraft.name.trim()}>
                Add supplier
              </button>
              </form>
            ) : null}
          </div>
        </section>

        <section className="section-card" aria-labelledby="orders-title">
          <div className="section-card-head">
            <h3 id="orders-title">Purchase orders</h3>
            <span className="muted text-sm">{orders.length} recorded</span>
          </div>
          <div className="section-card-body">
            {orders.length === 0 ? <p className="muted">No purchase orders yet.</p> : null}
            {orders.map((order) => (
              <div className="audit-row" key={order.id}>
                <div>
                  <strong>{order.code}</strong>
                  <div className="muted text-sm">
                    {order.supplier_name || order.supplier_id.slice(0, 8)} ·{" "}
                    {formatMoney(order.total_minor, "USD")} · {order.status}
                  </div>
                </div>
                {canManage && order.status !== "RECEIVED" && order.status !== "CANCELLED" ? (
                  <button className="btn ghost btn-sm" type="button" disabled={busy} onClick={() => void receive(order)}>
                    Receive
                  </button>
                ) : null}
              </div>
            ))}

            {canManage ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-3)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void createPurchaseOrder();
                }}
              >
              <div className="grid two">
                <label className="field">
                  PO code
                  <input
                    value={poDraft.code}
                    onChange={(event) => setPoDraft({ ...poDraft, code: event.target.value })}
                    required
                  />
                </label>
                <label className="field">
                  Supplier
                  <select
                    value={poDraft.supplier_id}
                    onChange={(event) => setPoDraft({ ...poDraft, supplier_id: event.target.value })}
                    required
                  >
                    <option value="">Select…</option>
                    {suppliers.map((supplier) => (
                      <option key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  Ingredient
                  <select
                    value={poDraft.ingredient_id}
                    onChange={(event) => setPoDraft({ ...poDraft, ingredient_id: event.target.value })}
                    required
                  >
                    <option value="">Select…</option>
                    {ingredients.map((ingredient) => (
                      <option key={ingredient.id} value={ingredient.id}>
                        {ingredient.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  Quantity
                  <input
                    type="number"
                    min={1}
                    value={poDraft.quantity}
                    onChange={(event) => setPoDraft({ ...poDraft, quantity: event.target.value })}
                  />
                </label>
                <label className="field">
                  Unit price (minor)
                  <input
                    type="number"
                    min={0}
                    value={poDraft.unit_price_minor}
                    onChange={(event) =>
                      setPoDraft({ ...poDraft, unit_price_minor: event.target.value })
                    }
                  />
                </label>
              </div>
              <button
                className="btn secondary"
                type="submit"
                disabled={busy || !poDraft.code.trim() || !poDraft.supplier_id || !poDraft.ingredient_id}
              >
                Create purchase order
              </button>
              </form>
            ) : null}
          </div>
        </section>
      </div>

      <section className="section-card" aria-labelledby="recipes-title">
        <div className="section-card-head">
          <h3 id="recipes-title">Recipes</h3>
          <span className="muted text-sm">Ingredients per menu item</span>
        </div>
        <div className="section-card-body">
          <label className="field">
            Menu item
            <select
              value={recipeMenuId}
              onChange={(event) => {
                setRecipeMenuId(event.target.value);
                setRecipeDraft([]);
              }}
            >
              <option value="">Select a menu item…</option>
              {menuItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.category} · {item.name}
                </option>
              ))}
            </select>
          </label>

          {recipeMenuId ? (
            <>
              <h4>Saved recipe</h4>
              {selectedRecipes.length === 0 ? <p className="muted">No ingredients saved yet.</p> : null}
              {selectedRecipes.map((row) => (
                <div className="list-row" key={row.id}>
                  <span>{row.ingredient_name}</span>
                  <span className="muted text-sm">
                    {row.quantity_per_serving} {row.ingredient_unit} per serving
                  </span>
                </div>
              ))}

              {canManage ? (
                <>
                  <h4>New recipe draft</h4>
                  {recipeDraft.length === 0 ? <p className="muted">Add ingredients to the draft.</p> : null}
                  {recipeDraft.map((row) => {
                    const ingredient = ingredients.find((entry) => entry.id === row.ingredient_id);
                    return (
                      <div className="list-row" key={row.ingredient_id}>
                        <span>{ingredient?.name ?? row.ingredient_id.slice(0, 8)}</span>
                        <span className="muted text-sm">
                          {row.quantity_per_serving} {ingredient?.unit ?? "units"}
                        </span>
                      </div>
                    );
                  })}
                  <div className="row" style={{ marginTop: "var(--space-2)" }}>
                    <select value={recipeItem} onChange={(event) => setRecipeItem(event.target.value)}>
                      <option value="">Add ingredient…</option>
                      {ingredients.map((ingredient) => (
                        <option key={ingredient.id} value={ingredient.id}>
                          {ingredient.name}
                        </option>
                      ))}
                    </select>
                    <button className="btn ghost btn-sm" type="button" onClick={addRecipeItem} disabled={!recipeItem}>
                      Add
                    </button>
                    <button
                      className="btn"
                      type="button"
                      disabled={busy || recipeDraft.length === 0}
                      onClick={() => void saveRecipe()}
                    >
                      Save recipe
                    </button>
                  </div>
                </>
              ) : null}
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
