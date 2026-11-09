import { useCallback, useEffect, useState } from "react";
import { apiFetch, type LowStockReport, ApiError } from "../../../lib/api";
import { useAuth } from "../../../lib/auth";
import { Link } from "react-router-dom";
import { formatMoney } from "../../../lib/api";

export default function InventoryOverviewPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [report, setReport] = useState<LowStockReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch<LowStockReport>("/api/v1/inventory/reports/low-stock");
      setReport(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load inventory overview.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const lowStock = report?.ingredients ?? [];

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}

      <div className="kpi-grid">
        <div className="kpi">
          <p className="kpi-label">Total tracked</p>
          <p className="kpi-value">{lowStock.length}</p>
          <p className="kpi-foot">ingredients at or below minimum</p>
        </div>
        <div className="kpi">
          <p className="kpi-label">Out of stock</p>
          <p className="kpi-value">
            {lowStock.filter((i) => i.current_stock <= 0).length}
          </p>
          <p className="kpi-foot">need immediate attention</p>
        </div>
        <div className="kpi">
          <p className="kpi-label">Low stock</p>
          <p className="kpi-value">
            {lowStock.filter((i) => i.current_stock > 0 && i.current_stock <= i.minimum_stock).length}
          </p>
          <p className="kpi-foot">approaching reorder point</p>
        </div>
        <div className="kpi">
          <p className="kpi-label">Estimated reorder value</p>
          <p className="kpi-value">{formatMoney(0, "NPR")}</p>
          <p className="kpi-foot">to bring low items to minimum</p>
        </div>
      </div>

      <section className="section-card">
        <div className="section-card-head">
          <h3>Items needing reorder</h3>
          {canManage ? (
            <Link to="/staff/inventory/ingredients" className="btn ghost btn-sm">
              Manage ingredients
            </Link>
          ) : null}
        </div>
        <div className="section-card-body">
          {busy ? (
            <p className="muted">Loading…</p>
          ) : lowStock.length === 0 ? (
            <div className="empty-state">
              <strong>All stocked up.</strong>
              <p className="muted text-sm">No ingredients are below their minimum level.</p>
            </div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ingredient</th>
                    <th className="num">SKU</th>
                    <th className="num">On hand</th>
                    <th className="num">Minimum</th>
                    <th className="num">Unit</th>
                    <th>Storage</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStock.map((ing) => (
                    <tr key={ing.id}>
                      <td>
                        <strong>{ing.name}</strong>
                      </td>
                      <td className="num muted text-sm">{ing.sku || "—"}</td>
                      <td className="num">{ing.current_stock}</td>
                      <td className="num">{ing.minimum_stock}</td>
                      <td className="num">{ing.unit}</td>
                      <td className="muted text-sm">{ing.storage_location || "—"}</td>
                      <td>
                        <span
                          className={`badge ${
                            ing.current_stock <= 0 ? "rejected" : "pending"
                          }`}
                        >
                          {ing.current_stock <= 0 ? "OUT_OF_STOCK" : "LOW_STOCK"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <section className="section-card">
        <div className="section-card-head">
          <h3>Quick actions</h3>
        </div>
        <div className="section-card-body">
          <div className="grid three">
            {canManage ? (
              <>
                <Link to="/staff/inventory/ingredients" className="quick-action">
                  <span>
                    <strong>Ingredients</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      SKU, category, storage &amp; batches
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                <Link to="/staff/inventory/purchases" className="quick-action">
                  <span>
                    <strong>Purchase orders</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Receive stock from suppliers
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                <Link to="/staff/inventory/movements" className="quick-action">
                  <span>
                    <strong>Stock movements</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Record waste, adjustments &amp; transfers
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                <Link to="/staff/inventory/batches" className="quick-action">
                  <span>
                    <strong>Batch tracking</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      FEFO &amp; expiry dates
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                <Link to="/staff/inventory/counts" className="quick-action">
                  <span>
                    <strong>Stock counts</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Blind count &amp; variance
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                <Link to="/staff/inventory/suppliers" className="quick-action">
                  <span>
                    <strong>Suppliers</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Vendor contact details
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
              </>
            ) : (
              <div className="empty-state">
                <strong>View-only inventory.</strong>
                <p className="muted text-sm">Ask your manager for inventory manage access.</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
