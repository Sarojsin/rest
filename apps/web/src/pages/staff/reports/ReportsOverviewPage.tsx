import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  formatMoney,
  ApiError,
  type SalesReport,
} from "../../../lib/api";
import { useAuth } from "../../../lib/auth";
import { Link } from "react-router-dom";

export default function ReportsOverviewPage() {
  const { has } = useAuth();
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

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading recorded sales…</p> : null}

      {forbidden ? (
        <div className="empty-state">
          <strong>Sales figures are restricted</strong>
          <span>
            Your role can run the floor but cannot read restaurant takings. Ask an owner or manager for the
            sales summary.
          </span>
        </div>
      ) : null}

      {report ? (
        <>
          <section className="report-grid" aria-label="Sales totals">
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
              <p className="muted">Orders</p>
              <p className="stat">{report.order_count}</p>
              <p className="kpi-foot">{report.accepted_order_count} accepted</p>
            </article>
            <article className="report-card">
              <p className="muted">Rejected or cancelled</p>
              <p className="stat">{report.cancelled_order_count}</p>
              <p className="kpi-foot">Never entered the kitchen</p>
            </article>
          </section>

          <section className="section-card">
            <div className="section-card-head">
              <h3>Report sections</h3>
            </div>
            <div className="section-card-body">
              <div className="grid three">
                <Link to="/staff/reports/sales" className="quick-action">
                  <span>
                    <strong>Sales detail</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Takings, top items &amp; average order
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                <Link to="/staff/reports/daily" className="quick-action">
                  <span>
                    <strong>Daily trend</strong>
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Orders &amp; sales per day
                    </p>
                  </span>
                  <span aria-hidden="true">▸</span>
                </Link>
                {has("inventory.read") ? (
                  <Link to="/staff/reports/inventory" className="quick-action">
                    <span>
                      <strong>Inventory</strong>
                      <p className="muted text-sm" style={{ margin: 0 }}>
                        Low stock, consumption &amp; waste
                      </p>
                    </span>
                    <span aria-hidden="true">▸</span>
                  </Link>
                ) : null}
                {has("audit.read") ? (
                  <Link to="/staff/reports/audit" className="quick-action">
                    <span>
                      <strong>Audit trail</strong>
                      <p className="muted text-sm" style={{ margin: 0 }}>
                        Every recorded change, filterable
                      </p>
                    </span>
                    <span aria-hidden="true">▸</span>
                  </Link>
                ) : null}
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
