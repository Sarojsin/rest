import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiFetch,
  type StockCount,
  type Ingredient,
  ApiError,
} from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

type CountItemDraft = {
  ingredient_id: string;
  expected_qty: string;
  counted_qty: string;
};

type CountDraft = {
  branch_id: string;
  count_date: string;
  notes: string;
  items: CountItemDraft[];
};

const EMPTY_COUNT_ITEM: CountItemDraft = {
  ingredient_id: "",
  expected_qty: "0",
  counted_qty: "0",
};

const EMPTY_COUNT_DRAFT: CountDraft = {
  branch_id: "",
  count_date: "",
  notes: "",
  items: [],
};

export default function StockCountsPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [counts, setCounts] = useState<StockCount[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [countDraft, setCountDraft] = useState<CountDraft>(EMPTY_COUNT_DRAFT);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [countList, ingredientList] = await Promise.all([
        apiFetch<StockCount[]>("/api/v1/inventory/stock-counts"),
        apiFetch<Ingredient[]>("/api/v1/inventory/ingredients"),
      ]);
      setCounts(countList);
      setIngredients(ingredientList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load stock counts.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const ingredientById = useMemo(() => {
    const map = new Map<string, Ingredient>();
    ingredients.forEach((ing) => map.set(ing.id, ing));
    return map;
  }, [ingredients]);

  const filtered = useMemo(() => {
    return counts.filter((count) => (!statusFilter || count.status === statusFilter));
  }, [counts, statusFilter]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The stock count action failed.");
    } finally {
      setBusy(false);
    }
  }

  function addCountItem() {
    setCountDraft({
      ...countDraft,
      items: [...countDraft.items, { ...EMPTY_COUNT_ITEM }],
    });
  }

  function removeCountItem(index: number) {
    setCountDraft({
      ...countDraft,
      items: countDraft.items.filter((_, i) => i !== index),
    });
  }

  function updateCountItem(index: number, field: keyof CountItemDraft, value: string) {
    const items = [...countDraft.items];
    items[index] = { ...items[index], [field]: value };
    setCountDraft({ ...countDraft, items });
  }

  function createStockCount() {
    return run(async () => {
      await apiFetch<StockCount>("/api/v1/inventory/stock-counts", {
        method: "POST",
        body: JSON.stringify({
          branch_id: countDraft.branch_id.trim() || null,
          count_date: countDraft.count_date || new Date().toISOString(),
          notes: countDraft.notes.trim() || null,
          items: countDraft.items.map((item) => ({
            ingredient_id: item.ingredient_id,
            expected_qty: Number(item.expected_qty) || 0,
            counted_qty: Number(item.counted_qty) || 0,
          })),
        }),
      });
      setCountDraft(EMPTY_COUNT_DRAFT);
      return "Stock count created.";
    });
  }

  function completeStockCount(countId: string) {
    return run(async () => {
      await apiFetch<StockCount>(`/api/v1/inventory/stock-counts/${countId}/complete`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      return "Stock count completed. Variances posted to stock ledger.";
    });
  }

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <select
            className="field"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
        {canManage ? (
          <button className="btn" type="button" onClick={() => {}}>
            + New stock count
          </button>
        ) : null}
      </div>

      <section className="section-card">
        <div className="section-card-head">
          <h3>Stock counts</h3>
          <span className="muted text-sm">{filtered.length} counts</span>
        </div>
        <div className="section-card-body">
          {busy ? (
            <p className="muted">Loading…</p>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <strong>No stock counts yet.</strong>
              <p className="muted text-sm">Run a blind count to reconcile physical stock with the ledger.</p>
            </div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Count date</th>
                    <th className="num">Branch</th>
                    <th className="num">Items</th>
                    <th className="num">Variances</th>
                    <th>Status</th>
                    <th className="num">Recorded</th>
                    {canManage ? <th style={{ width: "120px" }}>Action</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((count) => {
                    const varianceCount = count.items.filter((i) => i.variance_qty !== 0).length;
                    return (
                      <tr key={count.id}>
                        <td>
                          {new Date(count.count_date).toLocaleDateString()}
                        </td>
                        <td className="num muted text-sm">{count.branch_id ? count.branch_id.slice(0, 8) : "—"}</td>
                        <td className="num">{count.items.length}</td>
                        <td className="num">{varianceCount}</td>
                        <td>
                          <span
                            className={`badge ${
                              count.status === "COMPLETED" ? "accepted" : "draft"
                            }`}
                          >
                            {count.status}
                          </span>
                        </td>
                        <td className="num muted text-sm">
                          {new Date(count.created_at).toLocaleDateString()}
                        </td>
                        {canManage && count.status === "DRAFT" ? (
                          <td>
                            <button
                              className="btn ok btn-sm"
                              type="button"
                              disabled={busy}
                              onClick={() => void completeStockCount(count.id)}
                            >
                              Complete
                            </button>
                          </td>
                        ) : null}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {canManage ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Create stock count</h3>
          </div>
          <div className="section-card-body">
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void createStockCount();
              }}
            >
              <div className="grid three">
                <label className="field">
                  Branch ID (optional)
                  <input
                    value={countDraft.branch_id}
                    onChange={(event) => setCountDraft({ ...countDraft, branch_id: event.target.value })}
                    placeholder="optional"
                  />
                </label>
                <label className="field">
                  Count date
                  <input
                    type="datetime-local"
                    value={countDraft.count_date}
                    onChange={(event) => setCountDraft({ ...countDraft, count_date: event.target.value })}
                  />
                </label>
                <label className="field">
                  Notes
                  <input
                    value={countDraft.notes}
                    onChange={(event) => setCountDraft({ ...countDraft, notes: event.target.value })}
                    placeholder="e.g. Monthly blind count"
                  />
                </label>
              </div>

              <div style={{ marginTop: "var(--space-4)" }}>
                <h4 style={{ margin: "0 0 var(--space-2)" }}>Count items</h4>
                {countDraft.items.map((item, index) => {
                  const ingredient = ingredientById.get(item.ingredient_id);
                  return (
                    <div className="grid four" key={index} style={{ gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                      <label className="field">
                        Ingredient
                        <select
                          value={item.ingredient_id}
                          onChange={(event) => updateCountItem(index, "ingredient_id", event.target.value)}
                          required
                        >
                          <option value="">Select…</option>
                          {ingredients.map((ing) => (
                            <option key={ing.id} value={ing.id}>{ing.name}</option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        Expected qty
                        <input
                          type="number"
                          min={0}
                          value={item.expected_qty}
                          readOnly
                          onChange={(event) => updateCountItem(index, "expected_qty", event.target.value)}
                        />
                        <p className="field-hint">{ingredient ? ingredient.current_stock : ""} on hand</p>
                      </label>
                      <label className="field">
                        Counted qty
                        <input
                          type="number"
                          min={0}
                          value={item.counted_qty}
                          onChange={(event) => updateCountItem(index, "counted_qty", event.target.value)}
                          required
                        />
                      </label>
                      <button
                        type="button"
                        className="btn ghost btn-sm danger"
                        onClick={() => removeCountItem(index)}
                        style={{ alignSelf: "end" }}
                      >
                        Remove
                      </button>
                    </div>
                  );
                })}
                <button
                  type="button"
                  className="btn secondary btn-sm"
                  onClick={addCountItem}
                  disabled={busy}
                >
                  + Add item
                </button>
              </div>

              {countDraft.items.length === 0 && (
                <p className="muted text-sm">Add at least one item to create a count.</p>
              )}

              <button
                className="btn secondary"
                type="submit"
                disabled={busy || countDraft.items.length === 0}
              >
                Create stock count
              </button>
            </form>
          </div>
        </section>
      ) : null}
    </div>
  );
}
