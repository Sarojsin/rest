import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiFetch,
  type StockMovement,
  type Ingredient,
  ApiError,
} from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

type MovementDraft = {
  ingredient_id: string;
  movement_type: string;
  quantity: string;
  reason: string;
  batch_id: string;
  branch_id: string;
  idempotency_key: string;
};

const EMPTY_DRAFT: MovementDraft = {
  ingredient_id: "",
  movement_type: "RECEIVE",
  quantity: "1",
  reason: "",
  batch_id: "",
  branch_id: "",
  idempotency_key: "",
};

const MOVEMENT_TYPES: { value: string; label: string }[] = [
  { value: "RECEIVE", label: "Receive" },
  { value: "DEDUCT", label: "Deduct" },
  { value: "WASTE", label: "Waste" },
  { value: "ADJUST", label: "Adjust (signed)" },
  { value: "TRANSFER_IN", label: "Transfer in" },
  { value: "TRANSFER_OUT", label: "Transfer out" },
];

export default function MovementsPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [movementDraft, setMovementDraft] = useState<MovementDraft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [ingredientFilter, setIngredientFilter] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [movementList, ingredientList] = await Promise.all([
        apiFetch<StockMovement[]>("/api/v1/inventory/stock-movements"),
        apiFetch<Ingredient[]>("/api/v1/inventory/ingredients"),
      ]);
      setMovements(movementList);
      setIngredients(ingredientList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load stock movements.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    return movements.filter((movement) => {
      const matchesType = !typeFilter || movement.movement_type === typeFilter;
      const matchesIngredient =
        !ingredientFilter || movement.ingredient_id === ingredientFilter;
      return matchesType && matchesIngredient;
    });
  }, [movements, typeFilter, ingredientFilter]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The movement action failed.");
    } finally {
      setBusy(false);
    }
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
          batch_id: movementDraft.batch_id.trim() || null,
          branch_id: movementDraft.branch_id.trim() || null,
          idempotency_key: movementDraft.idempotency_key.trim() || null,
        }),
      });
      setMovementDraft(EMPTY_DRAFT);
      return "Stock movement recorded.";
    });
  }

  const ingredientById = useMemo(() => {
    const map = new Map<string, Ingredient>();
    ingredients.forEach((ing) => map.set(ing.id, ing));
    return map;
  }, [ingredients]);

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <select
            className="field"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
          >
            <option value="">All types</option>
            {MOVEMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <select
            className="field"
            value={ingredientFilter}
            onChange={(event) => setIngredientFilter(event.target.value)}
          >
            <option value="">All ingredients</option>
            {ingredients.map((ing) => (
              <option key={ing.id} value={ing.id}>{ing.name}</option>
            ))}
          </select>
        </div>
      </div>

      {canManage ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Record a stock movement</h3>
          </div>
          <div className="section-card-body">
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void recordMovement();
              }}
            >
              <div className="grid four">
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
                    required
                  >
                    {MOVEMENT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
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
                  Batch ID (optional)
                  <input
                    value={movementDraft.batch_id}
                    onChange={(event) =>
                      setMovementDraft({ ...movementDraft, batch_id: event.target.value })
                    }
                    placeholder="batch id…"
                  />
                </label>
                <label className="field">
                  Branch ID (optional)
                  <input
                    value={movementDraft.branch_id}
                    onChange={(event) =>
                      setMovementDraft({ ...movementDraft, branch_id: event.target.value })
                    }
                    placeholder="branch id…"
                  />
                </label>
                <label className="field">
                  Idempotency key (optional)
                  <input
                    value={movementDraft.idempotency_key}
                    onChange={(event) =>
                      setMovementDraft({ ...movementDraft, idempotency_key: event.target.value })
                    }
                    placeholder="prevents duplicates…"
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
          </div>
        </section>
      ) : null}

      <section className="section-card">
        <div className="section-card-head">
          <h3>Stock ledger</h3>
          <span className="muted text-sm">{filtered.length} movements</span>
        </div>
        <div className="section-card-body">
          {busy ? (
            <p className="muted">Loading…</p>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <strong>No movements yet.</strong>
              <p className="muted text-sm">Record a stock movement to start the ledger.</p>
            </div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Ingredient</th>
                    <th className="num">Qty</th>
                    <th className="num">New balance</th>
                    <th className="num">Batch</th>
                    <th className="num">Branch</th>
                    <th>Reason</th>
                    <th className="num">Recorded</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((movement) => {
                    const ingredient = ingredientById.get(movement.ingredient_id);
                    return (
                      <tr key={movement.id}>
                        <td>
                          <span
                            className={`badge ${
                              movement.movement_type === "RECEIVE"
                                ? "accepted"
                                : movement.movement_type === "DEDUCT" ||
                                  movement.movement_type === "WASTE"
                                  ? "rejected"
                                  : movement.movement_type === "ADJUST"
                                    ? "info"
                                    : "pending"
                            }`}
                          >
                            {movement.movement_type.replace("_", " ")}
                          </span>
                        </td>
                        <td>
                          {ingredient?.name ?? movement.ingredient_id.slice(0, 8)}
                        </td>
                        <td className="num">
                          {movement.quantity > 0 ? "+" : ""}{movement.quantity}
                        </td>
                        <td className="num">{movement.new_balance}</td>
                        <td className="num muted text-sm">{movement.batch_id ? movement.batch_id.slice(0, 8) : "—"}</td>
                        <td className="num muted text-sm">{movement.branch_id ? movement.branch_id.slice(0, 8) : "—"}</td>
                        <td className="muted text-sm">{movement.reason || "—"}</td>
                        <td className="num muted text-sm">
                          {new Date(movement.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
