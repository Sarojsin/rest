import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiFetch,
  type IngredientBatch,
  type Ingredient,
  ApiError,
  formatMoney,
} from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

type BatchDraft = {
  ingredient_id: string;
  batch_no: string;
  expiry_date: string;
  quantity: string;
  cost_per_unit_minor: string;
};

const EMPTY_BATCH_DRAFT: BatchDraft = {
  ingredient_id: "",
  batch_no: "",
  expiry_date: "",
  quantity: "0",
  cost_per_unit_minor: "0",
};

export default function BatchesPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [batches, setBatches] = useState<IngredientBatch[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [batchDraft, setBatchDraft] = useState<BatchDraft>(EMPTY_BATCH_DRAFT);
  const [includeExpired, setIncludeExpired] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [batchList, ingredientList] = await Promise.all([
        apiFetch<IngredientBatch[]>(
          `/api/v1/inventory/batches?include_expired=${includeExpired}`
        ),
        apiFetch<Ingredient[]>("/api/v1/inventory/ingredients"),
      ]);
      setBatches(batchList);
      setIngredients(ingredientList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load batches.");
    } finally {
      setBusy(false);
    }
  }, [includeExpired]);

  useEffect(() => {
    void load();
  }, [load]);

  const ingredientById = useMemo(() => {
    const map = new Map<string, Ingredient>();
    ingredients.forEach((ing) => map.set(ing.id, ing));
    return map;
  }, [ingredients]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The batch action failed.");
    } finally {
      setBusy(false);
    }
  }

  function createBatch() {
    return run(async () => {
      await apiFetch<IngredientBatch>("/api/v1/inventory/batches", {
        method: "POST",
        body: JSON.stringify({
          ingredient_id: batchDraft.ingredient_id,
          batch_no: batchDraft.batch_no.trim(),
          expiry_date: batchDraft.expiry_date || null,
          quantity: Number(batchDraft.quantity) || 0,
          cost_per_unit_minor: Number(batchDraft.cost_per_unit_minor) || 0,
        }),
      });
      setBatchDraft(EMPTY_BATCH_DRAFT);
      return "Batch created.";
    });
  }

  const now = new Date();

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <label className="field" style={{ margin: 0, fontSize: "var(--text-sm)", fontWeight: "600", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <input
              type="checkbox"
              checked={includeExpired}
              onChange={(event) => setIncludeExpired(event.target.checked)}
            />
            Include expired batches
          </label>
        </div>
        {canManage ? (
          <button className="btn" type="button" onClick={() => {}}>
            + Add batch
          </button>
        ) : null}
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ingredient</th>
              <th>Batch no.</th>
              <th className="num">Qty</th>
              <th className="num">Cost/unit</th>
              <th>Expiry</th>
              <th>Status</th>
              {canManage ? <th style={{ width: "120px" }}>Action</th> : null}
            </tr>
          </thead>
          <tbody>
            {batches.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted text-sm" style={{ textAlign: "center", padding: "var(--space-6)" }}>
                  No batches yet.
                </td>
              </tr>
            ) : (
              batches.map((batch) => {
                const ingredient = ingredientById.get(batch.ingredient_id);
                const expiry = batch.expiry_date ? new Date(batch.expiry_date) : null;
                const isExpired = expiry ? expiry < now : false;
                const isExpiringSoon = expiry ? expiry > now && expiry < new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000) : false;
                return (
                  <tr key={batch.id}>
                    <td>
                      {ingredient?.name ?? batch.ingredient_name ?? batch.ingredient_id.slice(0, 8)}
                    </td>
                    <td>
                      <strong>{batch.batch_no}</strong>
                    </td>
                    <td className="num">{batch.quantity}</td>
                    <td className="num">{formatMoney(batch.cost_per_unit_minor, "NPR")}</td>
                    <td className="num muted text-sm">
                      {batch.expiry_date ? new Date(batch.expiry_date).toLocaleDateString() : "No expiry"}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          isExpired
                            ? "rejected"
                            : isExpiringSoon
                              ? "pending"
                              : "accepted"
                        }`}
                      >
                        {isExpired ? "EXPIRED" : isExpiringSoon ? "EXPIRING SOON" : "FRESH"}
                      </span>
                    </td>
                    {canManage ? (
                      <td>
                        <button className="btn ghost btn-sm" type="button" disabled={busy}>
                          Edit
                        </button>
                      </td>
                    ) : null}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {canHaveBatchForm(canManage) ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Add batch</h3>
          </div>
          <div className="section-card-body">
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void createBatch();
              }}
            >
              <div className="grid four">
                <label className="field">
                  Ingredient
                  <select
                    value={batchDraft.ingredient_id}
                    onChange={(event) =>
                      setBatchDraft({ ...batchDraft, ingredient_id: event.target.value })
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
                  Batch no.
                  <input
                    value={batchDraft.batch_no}
                    onChange={(event) => setBatchDraft({ ...batchDraft, batch_no: event.target.value })}
                    required
                    placeholder="e.g. BATCH-2024-001"
                  />
                </label>
                <label className="field">
                  Expiry date
                  <input
                    type="date"
                    value={batchDraft.expiry_date}
                    onChange={(event) => setBatchDraft({ ...batchDraft, expiry_date: event.target.value })}
                  />
                </label>
                <label className="field">
                  Quantity
                  <input
                    type="number"
                    min={0}
                    value={batchDraft.quantity}
                    onChange={(event) => setBatchDraft({ ...batchDraft, quantity: event.target.value })}
                  />
                </label>
                <label className="field">
                  Cost per unit (minor)
                  <input
                    type="number"
                    min={0}
                    value={batchDraft.cost_per_unit_minor}
                    onChange={(event) => setBatchDraft({ ...batchDraft, cost_per_unit_minor: event.target.value })}
                  />
                </label>
              </div>
              <button className="btn secondary" type="submit" disabled={busy || !batchDraft.ingredient_id || !batchDraft.batch_no.trim()}>
                Add batch
              </button>
            </form>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function canHaveBatchForm(canManage: boolean) {
  return canManage;
}
