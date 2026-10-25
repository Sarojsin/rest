import { useEffect, useState } from "react";
import { apiFetch, ApiError, formatMoney, type AuditEvent, type SalesReport } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader } from "../../components/PageHeader";

export default function ReportsPage() {
  const { has } = useAuth();
  const [report, setReport] = useState<SalesReport | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiFetch<SalesReport>("/api/v1/reports/sales")
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 403 || err.status === 401)) {
          setForbidden(true);
        } else {
          setError("Could not load sales figures.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    if (has("audit.read")) {
      apiFetch<AuditEvent[]>("/api/v1/audit-events")
        .then((data) => {
          if (!cancelled) setEvents(data);
        })
        .catch(() => undefined);
    }
    return () => {
      cancelled = true;
    };
  }, [has]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Reporting"
        title="Sales & audit"
        sub="Every figure below is recorded server-side. The reporting endpoint has no date filter, so totals cover all orders for this restaurant, not today."
      />

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
      ) : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="top-items-title">
          <div className="section-card-head">
            <h3 id="top-items-title">Top items</h3>
            <span className="muted text-sm">By recorded sales</span>
          </div>
          <div className="section-card-body">
            {report && report.top_items.length > 0 ? (
              report.top_items.map((item) => (
                <div className="list-row" key={item.name}>
                  <span>
                    {item.quantity} × {item.name}
                  </span>
                  <strong className="numeric">{formatMoney(item.sales_minor, report.currency_code)}</strong>
                </div>
              ))
            ) : (
              <p className="muted">
                {forbidden
                  ? "Your role cannot read item sales."
                  : report
                    ? "No accepted items recorded yet."
                    : "Sales figures could not be loaded."}
              </p>
            )}
          </div>
        </section>

        <section className="section-card" aria-labelledby="audit-title">
          <div className="section-card-head">
            <h3 id="audit-title">Audit trail</h3>
            <span className="muted text-sm">{events.length > 0 ? `${events.length} events` : "Append-only"}</span>
          </div>
          <div className="section-card-body">
            {!has("audit.read") ? (
              <p className="muted">Your role cannot read the audit trail.</p>
            ) : events.length === 0 ? (
              <p className="muted">No audit events recorded yet.</p>
            ) : (
              events.slice(0, 20).map((event) => (
                <div className="audit-row" key={event.id}>
                  <div>
                    <span className="audit-action">{event.action}</span>
                    <div>{event.detail || `${event.entity_type}`}</div>
                  </div>
                  <time className="muted text-sm" dateTime={event.occurred_at}>
                    {new Date(event.occurred_at).toLocaleString()}
                  </time>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
