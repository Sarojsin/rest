import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiFetch,
  ApiError,
  type LowStockReport,
  type ConsumptionReport,
} from "../../../lib/api";

export default function ReportsInventoryPage() {
  const [lowStock, setLowStock] = useState<LowStockReport | null>(null);
  const [consumption, setConsumption] = useState<ConsumptionReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.allSettled([
        apiFetch<LowStockReport>("/api/v1/inventory/reports/low-stock"),
        apiFetch<ConsumptionReport>("/api/v1/inventory/reports/consumption"),
      ]);
      if (results[0].status === "fulfilled") setLowStock(results[0].value);
      if (results[1].status === "fulfilled") setConsumption(results[1].value);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load inventory reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const lowRows = useMemo(() => lowStock?.ingredients ?? [], [lowStock]);
  const consumptionRows = useMemo(
    () => [...(consumption?.consumption ?? [])].filter((row) => row.total_deducted > 0),
    [consumption]
  );

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading inventory reports…</p> : null}

      {lowStock ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Low stock</h3>
            <span className="muted text-sm">
              {lowStock.low_stock_count} ingredient{lowStock.low_stock_count === 1 ? "" : "s"} at or below minimum
            </span>
          </div>
          <div className="section-card-body">
            {lowRows.length === 0 ? (
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
                      <th className="num">On hand</th>
                      <th className="num">Minimum</th>
                      <th className="num">Unit</th>
                      <th>Storage</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowRows.map((ing) => (
                      <tr key={ing.id}>
                        <td>
                          <strong>{ing.name}</strong>
                          <div className="muted text-sm">{ing.sku || "—"}</div>
                        </td>
                        <td className="num">{ing.current_stock}</td>
                        <td className="num">{ing.minimum_stock}</td>
                        <td className="num">{ing.unit}</td>
                        <td className="muted text-sm">{ing.storage_location || "—"}</td>
                        <td>
                          <span className={`badge ${ing.current_stock <= 0 ? "rejected" : "pending"}`}>
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
      ) : null}

      {consumption ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Consumption to date</h3>
            <span className="muted text-sm">Deducted via kitchen tickets</span>
          </div>
          <div className="section-card-body">
            {consumptionRows.length === 0 ? (
              <p className="muted">No consumption recorded yet.</p>
            ) : (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Ingredient</th>
                      <th className="num">Total deducted</th>
                      <th className="num">Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consumptionRows.map((row) => (
                      <tr key={row.ingredient_id}>
                        <td>{row.ingredient_name ?? row.ingredient_id.slice(0, 8)}</td>
                        <td className="num">{row.total_deducted}</td>
                        <td className="num">{row.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      ) : null}

      {!lowStock && !consumption && !loading ? (
        <div className="empty-state">
          <strong>Inventory reports unavailable</strong>
          <p className="muted text-sm">Ask for the inventory feature to be enabled on this restaurant's plan.</p>
        </div>
      ) : null}
    </div>
  );
}
