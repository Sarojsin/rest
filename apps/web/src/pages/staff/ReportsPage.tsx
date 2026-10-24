import { useEffect, useState } from "react";
import { apiFetch, formatMoney, type AuditEvent, type SalesReport } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export default function ReportsPage() {
  const { has } = useAuth();
  const [report, setReport] = useState<SalesReport | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<SalesReport>("/api/v1/reports/sales")
      .then(setReport)
      .catch(() => setError("Could not load sales."));
    if (has("audit.read")) {
      apiFetch<AuditEvent[]>("/api/v1/audit-events").then(setEvents).catch(() => undefined);
    }
  }, [has]);

  return (
    <div>
      <h2>Owner reports</h2>
      {error ? <div className="error">{error}</div> : null}
      {report ? (
        <div className="grid three">
          <article className="card"><p className="muted">Gross sales</p><p className="stat">{formatMoney(report.gross_sales_minor, report.currency_code)}</p></article>
          <article className="card"><p className="muted">Collected</p><p className="stat">{formatMoney(report.collected_minor, report.currency_code)}</p></article>
          <article className="card"><p className="muted">Outstanding</p><p className="stat">{formatMoney(report.outstanding_minor, report.currency_code)}</p></article>
          <article className="card"><p className="muted">Accepted orders</p><p className="stat">{report.accepted_order_count}</p></article>
          <article className="card"><p className="muted">Rejected / cancelled</p><p className="stat">{report.cancelled_order_count}</p></article>
          <article className="card"><p className="muted">Tax</p><p className="stat">{formatMoney(report.tax_minor, report.currency_code)}</p></article>
        </div>
      ) : null}
      {report && report.top_items.length > 0 ? (
        <section className="card" style={{ marginTop: 16 }}>
          <h3>Top items</h3>
          {report.top_items.map((item) => (
            <div className="row" key={item.name}>
              <span>{item.quantity} x {item.name}</span>
              <span>{formatMoney(item.sales_minor, report.currency_code)}</span>
            </div>
          ))}
        </section>
      ) : null}
      {events.length > 0 ? (
        <section className="card" style={{ marginTop: 16 }}>
          <h3>Audit</h3>
          {events.slice(0, 20).map((event) => (
            <div className="row" key={event.id}>
              <span>{event.action}</span>
              <span className="muted">{new Date(event.occurred_at).toLocaleString()}</span>
            </div>
          ))}
        </section>
      ) : null}
    </div>
  );
}
