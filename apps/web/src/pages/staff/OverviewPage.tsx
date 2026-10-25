import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  apiFetch,
  formatMoney,
  type Order,
  type SalesReport,
  type ServiceCall,
  type Table,
} from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";

const POLL_MS = 15_000;

function waitingLabel(iso: string, now: number): string {
  const started = Date.parse(iso);
  if (Number.isNaN(started)) return "";
  const minutes = Math.max(0, Math.round((now - started) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "1 min ago";
  return `${minutes} min ago`;
}

export default function OverviewPage() {
  const { has } = useAuth();
  const [report, setReport] = useState<SalesReport | null>(null);
  const [tables, setTables] = useState<Table[]>([]);
  const [pending, setPending] = useState<Order[]>([]);
  const [calls, setCalls] = useState<ServiceCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const canReadOrders = has("orders.read");
  const canConfirm = has("orders.confirm_qr");
  const canReadCalls = has("tables.manage");
  const canReadReports = has("reports.read");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const jobs: Array<Promise<void>> = [];

      if (canReadReports) {
        jobs.push(
          apiFetch<SalesReport>("/api/v1/reports/sales")
            .then((data) => {
              if (!cancelled) setReport(data);
            })
            .catch(() => undefined)
        );
      }
      if (canReadOrders) {
        jobs.push(
          apiFetch<Table[]>("/api/v1/tables")
            .then((data) => {
              if (!cancelled) setTables(data);
            })
            .catch(() => undefined)
        );
      }
      if (canConfirm) {
        jobs.push(
          apiFetch<Order[]>("/api/v1/orders?status=PENDING_CONFIRMATION")
            .then((data) => {
              if (!cancelled) setPending(data);
            })
            .catch(() => undefined)
        );
      }
      if (canReadCalls) {
        jobs.push(
          apiFetch<ServiceCall[]>("/api/v1/service-calls?status=REQUESTED")
            .then((data) => {
              if (!cancelled) setCalls(data);
            })
            .catch(() => undefined)
        );
      }

      const results = await Promise.allSettled(jobs);
      if (cancelled) return;
      const failed = results.some((result) => result.status === "rejected");
      setError(failed ? "Some live data could not be loaded. The figures below may be incomplete." : null);
      setNow(Date.now());
    }

    void load();
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [canReadReports, canReadOrders, canConfirm, canReadCalls]);

  const occupied = useMemo(
    () => tables.filter((table) => table.occupancy !== "AVAILABLE").length,
    [tables]
  );
  const waiterCalls = calls.filter((call) => call.kind !== "KITCHEN");
  const kitchenCalls = calls.filter((call) => call.kind === "KITCHEN");
  const attentionCount = pending.length + calls.length;

  return (
    <>
      <PageHeader
        title="Overview"
        sub="Live service state next to the numbers the API has already recorded. Nothing here is estimated on the client."
        actions={
          <>
            {canConfirm ? (
              <Link className="btn" to="/staff/pending">
                Open order queue
                {pending.length > 0 ? ` (${pending.length})` : ""}
              </Link>
            ) : null}
            {canReadReports ? (
              <Link className="btn secondary" to="/staff/reports">
                Full reports
              </Link>
            ) : null}
          </>
        }
      />

      {error ? <div className="warning-banner">{error}</div> : null}

      <section className="kpi-grid" aria-label="Service status">
        {canReadOrders ? (
          <article className="kpi">
            <span className="kpi-label">Tables in service</span>
            <span className="kpi-value">
              {occupied}
              <span className="muted" style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                {" "}
                / {tables.length}
              </span>
            </span>
            <span className="kpi-foot">Occupied or awaiting checkout</span>
          </article>
        ) : null}

        {canConfirm ? (
          <article className="kpi">
            <span className="kpi-label">Awaiting confirmation</span>
            <span className="kpi-value">{pending.length}</span>
            <span className={`kpi-foot ${pending.length > 0 ? "is-alert" : ""}`}>
              {pending.length > 0 ? "Guests are waiting for staff" : "Queue is clear"}
            </span>
          </article>
        ) : null}

        {canReadCalls ? (
          <article className="kpi">
            <span className="kpi-label">Waiter calls</span>
            <span className="kpi-value">{waiterCalls.length}</span>
            <span className={`kpi-foot ${waiterCalls.length > 0 ? "is-alert" : ""}`}>
              {waiterCalls.length > 0 ? "Tables asking for service" : "No open calls"}
            </span>
          </article>
        ) : null}

        {canReadCalls ? (
          <article className="kpi">
            <span className="kpi-label">Food ready</span>
            <span className="kpi-value">{kitchenCalls.length}</span>
            <span className={`kpi-foot ${kitchenCalls.length > 0 ? "is-alert" : ""}`}>
              {kitchenCalls.length > 0 ? "Waiting for pickup" : "Kitchen has nothing waiting"}
            </span>
          </article>
        ) : null}
      </section>

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="attention-title">
          <div className="section-card-head">
            <h3 id="attention-title">Needs attention</h3>
            <span className="badge info">{attentionCount} open</span>
          </div>
          <div className="section-card-body">
            {attentionCount === 0 ? (
              <p className="muted">Nothing waiting. New guest orders and service calls appear here automatically.</p>
            ) : null}

            {pending.map((order) => (
              <div className="live-row" key={order.id}>
                <div className="live-row-main">
                  <span className="live-dot is-warn" aria-hidden="true" />
                  <div>
                    <strong>Guest order · {formatMoney(order.total_minor, order.items[0]?.currency_code)}</strong>
                    <div className="muted text-sm">
                      {order.items.map((item) => `${item.quantity}× ${item.item_name_snapshot}`).join(", ")}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <StatusBadge status={order.status} />
                  <div className="muted text-sm">{waitingLabel(order.submitted_at, now)}</div>
                </div>
              </div>
            ))}

            {calls.map((call) => (
              <div className="live-row" key={call.id}>
                <div className="live-row-main">
                  <span className={`live-dot ${call.kind === "KITCHEN" ? "" : "is-warn"}`} aria-hidden="true" />
                  <div>
                    <strong>
                      {call.table_display_name} · {call.kind === "KITCHEN" ? "Food ready for pickup" : "Called a waiter"}
                    </strong>
                    {call.items_summary ? <div className="muted text-sm">{call.items_summary}</div> : null}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <StatusBadge
                    status={call.kind === "KITCHEN" ? "READY" : "REQUESTED"}
                    label={call.kind === "KITCHEN" ? "Ready" : "Called"}
                  />
                  <div className="muted text-sm">{waitingLabel(call.requested_at, now)}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="stack">
          <section className="section-card" aria-labelledby="shortcuts-title">
            <div className="section-card-head">
              <h3 id="shortcuts-title">Shortcuts</h3>
            </div>
            <div className="section-card-body">
              <div className="quick-actions">
                {canReadOrders ? (
                  <Link className="quick-action" to="/staff/tables">
                    Floor &amp; printable QR codes <span aria-hidden="true">→</span>
                  </Link>
                ) : null}
                {has("menu.manage") ? (
                  <Link className="quick-action" to="/staff/menu">
                    Edit the published menu <span aria-hidden="true">→</span>
                  </Link>
                ) : null}
                {has("settings.manage") ? (
                  <Link className="quick-action" to="/staff/payments">
                    Payment QR methods <span aria-hidden="true">→</span>
                  </Link>
                ) : null}
                {has("kitchen.read") ? (
                  <Link className="quick-action" to="/staff/kitchen">
                    Kitchen board <span aria-hidden="true">→</span>
                  </Link>
                ) : null}
                {has("bills.issue") ? (
                  <Link className="quick-action" to="/staff/cashier">
                    Cashier &amp; bills <span aria-hidden="true">→</span>
                  </Link>
                ) : null}
              </div>
            </div>
          </section>

          {canReadReports && report ? (
            <section className="section-card" aria-labelledby="sales-title">
              <div className="section-card-head">
                <h3 id="sales-title">Recorded sales</h3>
                <span className="muted text-sm">All time</span>
              </div>
              <div className="section-card-body">
                <div className="list-row">
                  <span className="muted">Gross sales</span>
                  <strong className="numeric">{formatMoney(report.gross_sales_minor, report.currency_code)}</strong>
                </div>
                <div className="list-row">
                  <span className="muted">Collected</span>
                  <strong className="numeric">{formatMoney(report.collected_minor, report.currency_code)}</strong>
                </div>
                <div className="list-row">
                  <span className="muted">Outstanding</span>
                  <strong className="numeric">{formatMoney(report.outstanding_minor, report.currency_code)}</strong>
                </div>
                <div className="list-row">
                  <span className="muted">Accepted orders</span>
                  <strong className="numeric">{report.accepted_order_count}</strong>
                </div>
              </div>
            </section>
          ) : null}
        </div>
      </div>

      {canReadReports && report && report.top_items.length > 0 ? (
        <section className="section-card" aria-labelledby="top-items-title">
          <div className="section-card-head">
            <h3 id="top-items-title">Top items</h3>
            <span className="muted text-sm">By recorded sales</span>
          </div>
          <div className="section-card-body">
            {report.top_items.map((item) => (
              <div className="list-row" key={item.name}>
                <span>
                  {item.quantity} × {item.name}
                </span>
                <strong className="numeric">{formatMoney(item.sales_minor, report.currency_code)}</strong>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
