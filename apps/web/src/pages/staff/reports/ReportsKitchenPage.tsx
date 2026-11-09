import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError } from "../../../lib/api";

type TicketRow = {
  ticket_id: string;
  ticket_number: number;
  status: string;
  started_at: string | null;
  ready_at: string | null;
  prep_seconds: number;
};

type KitchenSpeedReport = {
  window_days: number;
  completed_ticket_count: number;
  avg_prep_seconds: number;
  fastest_prep_seconds: number;
  slowest_prep_seconds: number;
  slowest_tickets: TicketRow[];
};

function fmtSeconds(seconds: number | null): string {
  if (!seconds && seconds !== 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function ReportsKitchenPage() {
  const [report, setReport] = useState<KitchenSpeedReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const data = await apiFetch<KitchenSpeedReport>("/api/v1/reports/kitchen-speed");
      setReport(data);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 401)) {
        setForbidden(true);
      } else {
        setError(err instanceof ApiError ? err.detail : "Could not load kitchen speed report.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="empty-state">
        <strong>Kitchen speed report is restricted</strong>
        <span>
          Your role cannot read kitchen timing data. Ask an owner or manager for prep speed
          figures.
        </span>
      </div>
    );
  }

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading kitchen speed…</p> : null}

      {report ? (
        <>
          <section className="report-grid" aria-label="Kitchen speed summary">
            <article className="report-card">
              <p className="muted">Tickets completed</p>
              <p className="stat">{report.completed_ticket_count}</p>
              <p className="kpi-foot">Ready within last {report.window_days} days</p>
            </article>
            <article className="report-card">
              <p className="muted">Average prep time</p>
              <p className="stat">{fmtSeconds(report.avg_prep_seconds)}</p>
              <p className="kpi-foot">Created &rarr; ready</p>
            </article>
            <article className="report-card">
              <p className="muted">Fastest ticket</p>
              <p className="stat">{fmtSeconds(report.fastest_prep_seconds)}</p>
              <p className="kpi-foot">Quickest turnaround</p>
            </article>
            <article className="report-card">
              <p className="muted">Slowest ticket</p>
              <p className="stat">{fmtSeconds(report.slowest_prep_seconds)}</p>
              <p className="kpi-foot">Turnaround to investigate</p>
            </article>
          </section>

          <section className="section-card">
            <div className="section-card-head">
              <h3>Slowest tickets</h3>
              <span className="muted text-sm">{report.slowest_tickets.length} of {
                report.completed_ticket_count
              } completed tickets shown</span>
            </div>
            <div className="section-card-body">
              {report.slowest_tickets.length === 0 ? (
                <p className="muted">No completed tickets in this window.</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ticket</th>
                        <th className="num">Status</th>
                        <th className="num">Prep time</th>
                        <th>Started</th>
                        <th>Ready</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.slowest_tickets.map((ticket) => (
                        <tr key={ticket.ticket_id}>
                          <td>#{ticket.ticket_number}</td>
                          <td className="num">{ticket.status}</td>
                          <td className="num">{fmtSeconds(ticket.prep_seconds)}</td>
                          <td className="muted text-sm">{ticket.started_at ?? "—"}</td>
                          <td className="muted text-sm">{ticket.ready_at ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
