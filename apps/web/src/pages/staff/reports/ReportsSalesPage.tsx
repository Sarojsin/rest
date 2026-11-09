import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  formatMoney,
  ApiError,
  type SalesReport,
} from "../../../lib/api";

export default function ReportsSalesPage() {
  const [report, setReport] = useState<SalesReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const data = await apiFetch<SalesReport>("/api/v1/reports/sales");
      setReport(data);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 401)) {
        setForbidden(true);
      } else {
        setError(err instanceof ApiError ? err.detail : "Could not load sales figures.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const averageOrderMinor =
    report && report.accepted_order_count > 0
      ? Math.round(report.gross_sales_minor / report.accepted_order_count)
      : 0;

  if (forbidden) {
    return (
      <div className="empty-state">
        <strong>Sales figures are restricted</strong>
        <span>
          Your role can run the floor but cannot read restaurant takings. Ask an owner or manager for the
          sales summary.
        </span>
      </div>
    );
  }

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading sales…</p> : null}

      {report ? (
        <>
          <section className="report-grid" aria-label="Sales summary">
            <article className="report-card">
              <p className="muted">Average order value</p>
              <p className="stat">{formatMoney(averageOrderMinor, report.currency_code)}</p>
              <p className="kpi-foot">Gross sales / accepted orders</p>
            </article>
            <article className="report-card">
              <p className="muted">Gross sales</p>
              <p className="stat">{formatMoney(report.gross_sales_minor, report.currency_code)}</p>
              <p className="kpi-foot">Accepted items, before adjustments</p>
            </article>
            <article className="report-card">
              <p className="muted">Collected</p>
              <p className="stat">{formatMoney(report.collected_minor, report.currency_code)}</p>
              <p className="kpi-foot">Payments confirmed by staff</p>
            </article>
            <article className="report-card">
              <p className="muted">Outstanding</p>
              <p className="stat">{formatMoney(report.outstanding_minor, report.currency_code)}</p>
              <p className="kpi-foot">Issued and not yet settled</p>
            </article>
            <article className="report-card">
              <p className="muted">Tax</p>
              <p className="stat">{formatMoney(report.tax_minor, report.currency_code)}</p>
              <p className="kpi-foot">Sum of recorded tax</p>
            </article>
            <article className="report-card">
              <p className="muted">Acceptance rate</p>
              <p className="stat">
                {report.order_count > 0
                  ? `${Math.round((report.accepted_order_count / report.order_count) * 100)}%`
                  : "—"}
              </p>
              <p className="kpi-foot">
                {report.accepted_order_count} accepted of {report.order_count}
              </p>
            </article>
          </section>

          <section className="section-card" aria-labelledby="top-items-title">
            <div className="section-card-head">
              <h3 id="top-items-title">Top items</h3>
              <span className="muted text-sm">By recorded sales</span>
            </div>
            <div className="section-card-body">
              {report.top_items.length > 0 ? (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th className="num">Qty sold</th>
                        <th className="num">Sales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.top_items.map((item) => (
                        <tr key={item.name}>
                          <td>
                            <strong>{item.name}</strong>
                          </td>
                          <td className="num">{item.quantity}</td>
                          <td className="num">
                            {formatMoney(item.sales_minor, report.currency_code)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="muted">No accepted items recorded yet.</p>
              )}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
