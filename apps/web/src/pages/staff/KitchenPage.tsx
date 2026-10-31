import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch, ApiError, type KitchenTicket, type KitchenTicketItem } from "../../lib/api";
import { useAuth } from "../../lib/auth";

const POLL_MS = 4000;
const LATE_AFTER_MS = 12 * 60_000;

const COLUMNS = [
  {
    key: "NEW",
    title: "New",
    hint: "Accepted, not started",
    className: "is-new",
    empty: "No new tickets. Accepted guest orders land here.",
  },
  {
    key: "IN_PROGRESS",
    title: "Cooking",
    hint: "On the line right now",
    className: "is-cooking",
    empty: "Nothing on the line.",
  },
  {
    key: "READY",
    title: "Ready",
    hint: "Waiting for pickup",
    className: "is-ready",
    empty: "Nothing waiting for pickup.",
  },
] as const;

function elapsed(iso: string, now: number): string {
  const started = Date.parse(iso);
  if (Number.isNaN(started)) return "";
  const ms = Math.max(0, now - started);
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return "<1 min";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h ${minutes % 60} min`;
}

function isLate(iso: string, now: number): boolean {
  const started = Date.parse(iso);
  return !Number.isNaN(started) && now - started > LATE_AFTER_MS;
}

export default function KitchenPage() {
  const { has } = useAuth();
  const canUpdate = has("kitchen.update");
  const [tickets, setTickets] = useState<KitchenTicket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const mounted = useRef(true);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<KitchenTicket[]>("/api/v1/kitchen/tickets");
      if (!mounted.current) return;
      setTickets(data);
      setError(null);
    } catch {
      if (mounted.current) setError("Live ticket feed is unavailable. Retrying automatically…");
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void load();
    const poll = window.setInterval(() => void load(), POLL_MS);
    const clock = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => {
      mounted.current = false;
      window.clearInterval(poll);
      window.clearInterval(clock);
    };
  }, [load]);

  async function setItemStatus(item: KitchenTicketItem, status: "PREPARING" | "READY") {
    setBusyId(item.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await apiFetch<KitchenTicket>(
        `/api/v1/kitchen/ticket-items/${item.id}/status`,
        { method: "POST", body: JSON.stringify({ status }) }
      );
      setTickets((prev) => prev.map((ticket) => (ticket.id === updated.id ? updated : ticket)));
      setNow(Date.now());
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Could not update ${item.item_name ?? "item"}: ${err.detail}`
          : "Could not update the item."
      );
    } finally {
      setBusyId(null);
    }
  }

  async function markReadyAndCallWaiter(ticket: KitchenTicket) {
    setBusyId(ticket.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await apiFetch<KitchenTicket>(
        `/api/v1/kitchen/tickets/${ticket.id}/call-waiter`,
        { method: "POST" }
      );
      setTickets((prev) => prev.map((row) => (row.id === updated.id ? updated : row)));
      setNotice(`Ticket ${ticket.ticket_number} marked ready and service called.`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not signal the service team."
      );
    } finally {
      setBusyId(null);
    }
  }

  const grouped = useMemo(() => {
    const map: Record<string, KitchenTicket[]> = { NEW: [], IN_PROGRESS: [], READY: [] };
    for (const ticket of tickets) {
      const bucket = ticket.status === "READY" ? "READY" : ticket.status === "NEW" ? "NEW" : "IN_PROGRESS";
      map[bucket].push(ticket);
    }
    return map;
  }, [tickets]);

  const openCount = grouped.NEW.length + grouped.IN_PROGRESS.length;

  return (
    <>
      <div className="ops-page-head">
        <div>
          <h1>Kitchen board</h1>
          <p>
            {openCount === 0
              ? "No open tickets."
              : `${openCount} open ticket${openCount === 1 ? "" : "s"} on the line.`}{" "}
            Tickets only appear after staff accept a QR order.
          </p>
        </div>
        <div className="page-actions">
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh now
          </button>
        </div>
      </div>

      {error ? <div className="error no-print">{error}</div> : null}
      {notice ? <div className="notice no-print">{notice}</div> : null}

      <div className="ops-board">
        {COLUMNS.map((column) => {
          const columnTickets = grouped[column.key];
          return (
            <section className={`ops-column ${column.className}`} key={column.key} aria-label={`${column.title} tickets`}>
              <div className="ops-column-head">
                <div>
                  <h2>{column.title}</h2>
                  <span className="muted text-sm">{column.hint}</span>
                </div>
                <span className="ops-column-count">{columnTickets.length}</span>
              </div>

              {columnTickets.length === 0 ? (
                <p className="ops-empty">{column.empty}</p>
              ) : null}

              {columnTickets.map((ticket) => {
                const ticketBusy = busyId === ticket.id;
                const openItems = ticket.items.filter(
                  (item) => item.status !== "READY" && item.status !== "SERVED" && item.status !== "CANCELLED"
                );
                const activeItems = ticket.items.filter((item) => item.status !== "CANCELLED");
                const itemCount = activeItems.reduce((total, item) => total + item.quantity_snapshot, 0);
                // Once nothing is cooking the created-at clock stops being
                // meaningful: measure how long the food has been waiting
                // instead of claiming the kitchen is running long.
                const doneCooking =
                  activeItems.length > 0 &&
                  activeItems.every((item) => item.status === "READY" || item.status === "SERVED");
                const allServed = activeItems.length > 0 && activeItems.every((item) => item.status === "SERVED");
                const timeRef = doneCooking ? (ticket.ready_at ?? ticket.created_at) : ticket.created_at;
                const late = !doneCooking && isLate(ticket.created_at, now);
                return (
                  <article
                    className={`ticket-card ${
                      column.key === "NEW" ? "is-new" : column.key === "READY" ? "is-ready" : "is-cooking"
                    }`}
                    key={ticket.id}
                  >
                    <div className="ticket-head">
                      <div>
                        <h3 className="ticket-number">Ticket {ticket.ticket_number}</h3>
                        <p className="ticket-table">
                          {ticket.table_display_name ?? "Table unknown"} · {itemCount} item
                          {itemCount === 1 ? "" : "s"}
                        </p>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div className={`ticket-time ${late ? "is-late" : ""}`}>{elapsed(timeRef, now)}</div>
                        {allServed ? (
                          <span className="muted text-sm">delivered</span>
                        ) : doneCooking ? (
                          <span className="muted text-sm">waiting for pickup</span>
                        ) : late ? (
                          <span className="muted text-sm">running long</span>
                        ) : null}
                      </div>
                    </div>

                    <ul className="ticket-items">
                      {ticket.items.map((item) => (
                        <li className={`ticket-item ${item.status === "READY" ? "is-ready" : ""}`} key={item.id}>
                          <div className="ticket-item-main">
                            <div className="ticket-item-name">
                              <span className="ticket-qty">{item.quantity_snapshot}×</span>{" "}
                              {item.item_name ?? "Item"}
                            </div>
                            {item.instructions_snapshot ? (
                              <p className="ticket-item-note">Note: {item.instructions_snapshot}</p>
                            ) : null}
                            <div className="ticket-item-state">
                              {item.status === "CANCELLED" ? "Cancelled" : item.status === "SERVED" ? "Served" : item.status === "READY" ? "Ready" : item.status === "PREPARING" ? "Cooking" : "Not started"}
                            </div>
                          </div>
                          {canUpdate && item.status !== "CANCELLED" && item.status !== "SERVED" ? (
                            <div className="ticket-item-actions">
                              {item.status === "NEW" ? (
                                <button
                                  className="btn btn-sm"
                                  type="button"
                                  disabled={busyId === item.id}
                                  onClick={() => void setItemStatus(item, "PREPARING")}
                                >
                                  Start
                                </button>
                              ) : null}
                              {item.status === "PREPARING" ? (
                                <button
                                  className="btn ok btn-sm"
                                  type="button"
                                  disabled={busyId === item.id}
                                  onClick={() => void setItemStatus(item, "READY")}
                                >
                                  Ready
                                </button>
                              ) : null}
                              {item.status === "READY" ? (
                                <span className="muted text-sm">With the waiter</span>
                              ) : null}
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>

                    {canUpdate ? (
                      <div className="ticket-foot">
                        {column.key === "READY" ? (
                          <button
                            className="btn secondary"
                            type="button"
                            disabled={ticketBusy}
                            onClick={() => void markReadyAndCallWaiter(ticket)}
                          >
                            Call service again
                          </button>
                        ) : (
                          <button
                            className="btn ok"
                            type="button"
                            disabled={ticketBusy || openItems.length === 0}
                            onClick={() => void markReadyAndCallWaiter(ticket)}
                          >
                            {ticketBusy ? "Signalling…" : "All ready — call waiter"}
                          </button>
                        )}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </section>
          );
        })}
      </div>

      <p className="muted text-sm" style={{ marginTop: "var(--space-5)" }}>
        Item states move new → cooking → ready. Serving the food at the table is the
        waiter&apos;s job — press{" "}
        <strong>All ready — call waiter</strong> when plating is done; that also notifies the floor bell.{" "}
        {openCount === 0 ? <Link to="/staff">Back to dashboard</Link> : null}
      </p>
    </>
  );
}
