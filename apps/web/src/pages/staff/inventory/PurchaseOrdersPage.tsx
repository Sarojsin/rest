import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  type PurchaseOrder,
  type Supplier,
  type Ingredient,
  ApiError,
  formatMoney,
} from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

type PODraft = {
  code: string;
  supplier_id: string;
  ingredient_id: string;
  quantity: string;
  unit_price_minor: string;
};

const EMPTY_PODRAFT: PODraft = {
  code: "",
  supplier_id: "",
  ingredient_id: "",
  quantity: "1",
  unit_price_minor: "0",
};

export default function PurchaseOrdersPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [poDraft, setPoDraft] = useState<PODraft>(EMPTY_PODRAFT);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [orderList, supplierList, ingredientList] = await Promise.all([
        apiFetch<PurchaseOrder[]>("/api/v1/inventory/purchase-orders"),
        apiFetch<Supplier[]>("/api/v1/inventory/suppliers"),
        apiFetch<Ingredient[]>("/api/v1/inventory/ingredients"),
      ]);
      setOrders(orderList);
      setSuppliers(supplierList);
      setIngredients(ingredientList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load purchase orders.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The purchase order action failed.");
    } finally {
      setBusy(false);
    }
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
      setPoDraft(EMPTY_PODRAFT);
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

  const statuses = ["DRAFT", "SUBMITTED", "RECEIVED", "CANCELLED"];

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <select
            className="field"
            value=""
            onChange={() => {}}
          >
            <option value="">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
        {canManage ? (
          <button className="btn" type="button" onClick={() => {}}>
            + Create purchase order
          </button>
        ) : null}
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>PO code</th>
              <th>Supplier</th>
              <th className="num">Total</th>
              <th className="num">Items</th>
              <th>Status</th>
              <th className="num">Expected</th>
              {canManage ? <th style={{ width: "120px" }}>Action</th> : null}
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted text-sm" style={{ textAlign: "center", padding: "var(--space-6)" }}>
                  No purchase orders yet.
                </td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr key={order.id}>
                  <td>
                    <strong>{order.code}</strong>
                  </td>
                  <td>{order.supplier_name || order.supplier_id.slice(0, 8)}</td>
                  <td className="num">{formatMoney(order.total_minor, "NPR")}</td>
                  <td className="num">{order.items.length}</td>
                  <td>
                    <span
                      className={`badge ${
                        order.status === "RECEIVED"
                          ? "accepted"
                          : order.status === "CANCELLED"
                            ? "rejected"
                            : order.status === "SUBMITTED"
                              ? "pending"
                              : "draft"
                      }`}
                    >
                      {order.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="num muted text-sm">
                    {order.expected_date ? new Date(order.expected_date).toLocaleDateString() : "—"}
                  </td>
                  {canManage && order.status !== "RECEIVED" && order.status !== "CANCELLED" ? (
                    <td>
                      <button
                        className="btn ghost btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void receive(order)}
                      >
                        Receive
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {canManage ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Create purchase order</h3>
          </div>
          <div className="section-card-body">
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void createPurchaseOrder();
              }}
            >
              <div className="grid three">
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
                    onChange={(event) => setPoDraft({ ...poDraft, unit_price_minor: event.target.value })}
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
          </div>
        </section>
      ) : null}
    </div>
  );
}
