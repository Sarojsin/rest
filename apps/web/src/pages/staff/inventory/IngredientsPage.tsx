import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, type Ingredient, ApiError, formatMoney } from "../../../lib/api";
import { useAuth } from "../../../lib/auth";
import { Link } from "react-router-dom";

type IngredientDraft = {
  name: string;
  code: string;
  sku: string;
  unit: string;
  base_unit: string;
  category: string;
  unit_conversions: string;
  current_stock: string;
  minimum_stock: string;
  cost_per_unit_minor: string;
  storage_location: string;
  branch_id: string;
  supplier_id: string;
};

const EMPTY_INGREDIENT: IngredientDraft = {
  name: "",
  code: "",
  sku: "",
  unit: "pieces",
  base_unit: "pieces",
  category: "",
  unit_conversions: "",
  current_stock: "0",
  minimum_stock: "0",
  cost_per_unit_minor: "0",
  storage_location: "",
  branch_id: "",
  supplier_id: "",
};

export default function IngredientsPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [ingredientDraft, setIngredientDraft] = useState<IngredientDraft>(EMPTY_INGREDIENT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<IngredientDraft>(EMPTY_INGREDIENT);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const ingredientList = await apiFetch<Ingredient[]>("/api/v1/inventory/ingredients");
      setIngredients(ingredientList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load ingredients.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    return ingredients.filter((ing) => {
      const text = search.toLowerCase();
      const matchesText =
        ing.name.toLowerCase().includes(text) ||
        (ing.sku?.toLowerCase().includes(text) ?? false) ||
        (ing.code?.toLowerCase().includes(text) ?? false);
      const matchesStatus = !statusFilter || ing.status === statusFilter;
      return matchesText && matchesStatus;
    });
  }, [ingredients, search, statusFilter]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else if (err instanceof Error && err.message) {
        setError(err.message);
      } else {
        setError("The ingredient action failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  function createIngredient() {
    return run(async () => {
      const conversions: Record<string, number> = {};
      if (ingredientDraft.unit_conversions.trim()) {
        try {
          Object.assign(conversions, JSON.parse(ingredientDraft.unit_conversions));
        } catch {
          throw new Error("Unit conversions must be valid JSON, e.g. {\"kg\": 1000}");
        }
      }
      await apiFetch<Ingredient>("/api/v1/inventory/ingredients", {
        method: "POST",
        body: JSON.stringify({
          name: ingredientDraft.name.trim(),
          code: ingredientDraft.code.trim() || null,
          sku: ingredientDraft.sku.trim() || null,
          unit: ingredientDraft.unit.trim() || "pieces",
          base_unit: ingredientDraft.base_unit.trim() || "pieces",
          category: ingredientDraft.category.trim() || null,
          unit_conversions: conversions,
          current_stock: Number(ingredientDraft.current_stock) || 0,
          minimum_stock: Number(ingredientDraft.minimum_stock) || 0,
          cost_per_unit_minor: Number(ingredientDraft.cost_per_unit_minor) || 0,
          storage_location: ingredientDraft.storage_location.trim() || null,
          branch_id: ingredientDraft.branch_id.trim() || null,
          supplier_id: ingredientDraft.supplier_id.trim() || null,
        }),
      });
      setIngredientDraft(EMPTY_INGREDIENT);
      return "Ingredient added.";
    });
  }

  function updateIngredient() {
    return run(async () => {
      const conversions: Record<string, number> = {};
      if (editDraft.unit_conversions.trim()) {
        try {
          Object.assign(conversions, JSON.parse(editDraft.unit_conversions));
        } catch {
          throw new Error("Unit conversions must be valid JSON, e.g. {\"kg\": 1000}");
        }
      }
      await apiFetch<Ingredient>(`/api/v1/inventory/ingredients/${editingId}`, {
        method: "PUT",
        body: JSON.stringify({
          name: editDraft.name.trim(),
          code: editDraft.code.trim() || null,
          sku: editDraft.sku.trim() || null,
          unit: editDraft.unit.trim() || "pieces",
          base_unit: editDraft.base_unit.trim() || "pieces",
          category: editDraft.category.trim() || null,
          unit_conversions: conversions,
          current_stock: Number(editDraft.current_stock) || 0,
          minimum_stock: Number(editDraft.minimum_stock) || 0,
          cost_per_unit_minor: Number(editDraft.cost_per_unit_minor) || 0,
          storage_location: editDraft.storage_location.trim() || null,
          branch_id: editDraft.branch_id.trim() || null,
          supplier_id: editDraft.supplier_id.trim() || null,
        }),
      });
      setEditingId(null);
      return "Ingredient updated.";
    });
  }

  function startEdit(ingredient: Ingredient) {
    setEditingId(ingredient.id);
    setEditDraft({
      name: ingredient.name,
      code: ingredient.code ?? "",
      sku: ingredient.sku ?? "",
      unit: ingredient.unit,
      base_unit: ingredient.base_unit,
      category: ingredient.category ?? "",
      unit_conversions: ingredient.unit_conversions ? JSON.stringify(ingredient.unit_conversions) : "",
      current_stock: String(ingredient.current_stock),
      minimum_stock: String(ingredient.minimum_stock),
      cost_per_unit_minor: String(ingredient.cost_per_unit_minor),
      storage_location: ingredient.storage_location ?? "",
      branch_id: ingredient.branch_id ?? "",
      supplier_id: ingredient.supplier_id ?? "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditDraft(EMPTY_INGREDIENT);
  }

  const statuses = ["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"];

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <input
            className="field"
            placeholder="Search by name, SKU or code…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <select
            className="field"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
        {canManage ? (
          <Link to="#" onClick={(e) => { e.preventDefault(); setEditingId(null); setIngredientDraft(EMPTY_INGREDIENT); }}>
            <button className="btn" type="button">+ Add ingredient</button>
          </Link>
        ) : null}
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ingredient</th>
              <th className="num">SKU</th>
              <th className="num">Category</th>
              <th className="num">On hand</th>
              <th className="num">Min</th>
              <th className="num">Unit</th>
              <th className="num">Cost/unit</th>
              <th>Storage</th>
              <th>Branch</th>
              <th>Status</th>
              {canManage ? <th style={{ width: "220px" }}>Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="muted text-sm" style={{ textAlign: "center", padding: "var(--space-6)" }}>
                  No ingredients found.
                </td>
              </tr>
            ) : (
              filtered.map((ingredient) => (
                <tr key={ingredient.id}>
                  <td>
                    <strong>{ingredient.name}</strong>
                    <div className="muted text-sm">{ingredient.code || ingredient.sku || "—"}</div>
                  </td>
                  <td className="num muted text-sm">{ingredient.category || "—"}</td>
                  <td className="num">{ingredient.current_stock}</td>
                  <td className="num">{ingredient.minimum_stock}</td>
                  <td className="num">{ingredient.base_unit}</td>
                  <td className="num">{formatMoney(ingredient.cost_per_unit_minor, "NPR")}</td>
                  <td className="muted text-sm">{ingredient.storage_location || "—"}</td>
                  <td className="muted text-sm">{ingredient.branch_id ? ingredient.branch_id.slice(0, 8) : "—"}</td>
                  <td>
                    <span
                      className={`badge ${
                        ingredient.status === "IN_STOCK"
                          ? "accepted"
                          : ingredient.status === "LOW_STOCK"
                            ? "pending"
                            : "rejected"
                      }`}
                    >
                      {ingredient.status.replace("_", " ")}
                    </span>
                  </td>
                  {canManage ? (
                    <td>
                      <div className="row" style={{ gap: "var(--space-2)" }}>
                        <button
                          className="btn ghost btn-sm"
                          type="button"
                          onClick={() => startEdit(ingredient)}
                        >
                          Edit
                        </button>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {canManage ? (
        <>
          {editingId ? (
            <section className="section-card">
              <div className="section-card-head">
                <h3>Edit ingredient</h3>
                <button className="btn ghost btn-sm" type="button" onClick={cancelEdit}>
                  Cancel
                </button>
              </div>
              <div className="section-card-body">
                <form
                  className="stack"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void updateIngredient();
                  }}
                >
                  <div className="grid three">
                    <label className="field">
                      Name
                      <input
                        value={editDraft.name}
                        onChange={(event) => setEditDraft({ ...editDraft, name: event.target.value })}
                        required
                      />
                    </label>
                    <label className="field">
                      Code
                      <input
                        value={editDraft.code}
                        onChange={(event) => setEditDraft({ ...editDraft, code: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      SKU
                      <input
                        value={editDraft.sku}
                        onChange={(event) => setEditDraft({ ...editDraft, sku: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Unit
                      <input
                        value={editDraft.unit}
                        onChange={(event) => setEditDraft({ ...editDraft, unit: event.target.value })}
                        required
                      />
                    </label>
                    <label className="field">
                      Base unit
                      <input
                        value={editDraft.base_unit}
                        onChange={(event) => setEditDraft({ ...editDraft, base_unit: event.target.value })}
                        required
                      />
                    </label>
                    <label className="field">
                      Category
                      <input
                        value={editDraft.category}
                        onChange={(event) => setEditDraft({ ...editDraft, category: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Current stock
                      <input
                        type="number"
                        min={0}
                        value={editDraft.current_stock}
                        onChange={(event) => setEditDraft({ ...editDraft, current_stock: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Minimum stock
                      <input
                        type="number"
                        min={0}
                        value={editDraft.minimum_stock}
                        onChange={(event) => setEditDraft({ ...editDraft, minimum_stock: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Cost per unit (minor)
                      <input
                        type="number"
                        min={0}
                        value={editDraft.cost_per_unit_minor}
                        onChange={(event) => setEditDraft({ ...editDraft, cost_per_unit_minor: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Storage location
                      <input
                        value={editDraft.storage_location}
                        onChange={(event) => setEditDraft({ ...editDraft, storage_location: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Branch ID
                      <input
                        value={editDraft.branch_id}
                        onChange={(event) => setEditDraft({ ...editDraft, branch_id: event.target.value })}
                        placeholder="optional"
                      />
                    </label>
                    <label className="field">
                      Supplier ID
                      <input
                        value={editDraft.supplier_id}
                        onChange={(event) => setEditDraft({ ...editDraft, supplier_id: event.target.value })}
                        placeholder="optional"
                      />
                    </label>
                    <label className="field">
                      Unit conversions (JSON)
                      <textarea
                        value={editDraft.unit_conversions}
                        onChange={(event) =>
                          setEditDraft({ ...editDraft, unit_conversions: event.target.value })
                        }
                        placeholder='{"kg": 1000}'
                      />
                      <p className="field-hint">Conversion factors from base unit, e.g. {"{"}kg: 1000{"}"} means 1 base unit = 1000 of this unit.</p>
                    </label>
                  </div>
                  <button className="btn" type="submit" disabled={busy || !editDraft.name.trim()}>
                    Save changes
                  </button>
                </form>
              </div>
            </section>
          ) : (
            <section className="section-card">
              <div className="section-card-head">
                <h3>Add ingredient</h3>
              </div>
              <div className="section-card-body">
                <form
                  className="stack"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void createIngredient();
                  }}
                >
                  <div className="grid three">
                    <label className="field">
                      Name
                      <input
                        value={ingredientDraft.name}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, name: event.target.value })}
                        required
                      />
                    </label>
                    <label className="field">
                      Code
                      <input
                        value={ingredientDraft.code}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, code: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      SKU
                      <input
                        value={ingredientDraft.sku}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, sku: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Unit
                      <input
                        value={ingredientDraft.unit}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, unit: event.target.value })}
                        required
                      />
                    </label>
                    <label className="field">
                      Base unit
                      <input
                        value={ingredientDraft.base_unit}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, base_unit: event.target.value })}
                        required
                      />
                    </label>
                    <label className="field">
                      Category
                      <input
                        value={ingredientDraft.category}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, category: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Current stock
                      <input
                        type="number"
                        min={0}
                        value={ingredientDraft.current_stock}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, current_stock: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Minimum stock
                      <input
                        type="number"
                        min={0}
                        value={ingredientDraft.minimum_stock}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, minimum_stock: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Cost per unit (minor)
                      <input
                        type="number"
                        min={0}
                        value={ingredientDraft.cost_per_unit_minor}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, cost_per_unit_minor: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Storage location
                      <input
                        value={ingredientDraft.storage_location}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, storage_location: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      Branch ID
                      <input
                        value={ingredientDraft.branch_id}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, branch_id: event.target.value })}
                        placeholder="optional"
                      />
                    </label>
                    <label className="field">
                      Supplier ID
                      <input
                        value={ingredientDraft.supplier_id}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, supplier_id: event.target.value })}
                        placeholder="optional"
                      />
                    </label>
                    <label className="field">
                      Unit conversions (JSON)
                      <textarea
                        value={ingredientDraft.unit_conversions}
                        onChange={(event) => setIngredientDraft({ ...ingredientDraft, unit_conversions: event.target.value })}
                        placeholder='{"kg": 1000}'
                      />
                      <p className="field-hint">Conversion factors from base unit, e.g. {"{"}kg: 1000{"}"} means 1 base unit = 1000 of this unit.</p>
                    </label>
                  </div>
                  <button className="btn" type="submit" disabled={busy || !ingredientDraft.name.trim()}>
                    Add ingredient
                  </button>
                </form>
              </div>
            </section>
          )}
        </>
      ) : null}
    </div>
  );
}
