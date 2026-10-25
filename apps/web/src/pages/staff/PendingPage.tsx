import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, formatMoney, ApiError, type Order, type ServiceCall } from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { Sheet } from "../../components/Sheet";
import { StatusBadge } from "../../components/StatusBadge";

const POLL_MS = 4000;

function minutesAgo(iso: string): string {
  const started = Date.parse(iso);
  if (Number.isNaN(started)) return "";
  const minutes = Math.max(0, Math.round((Date.now() - started) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "1 min ago";
  return `${minutes} min ago`;
}

export default function PendingPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [calls, setCalls] = useState<ServiceCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<Order | null>(null);
  const [rejectNote, setRejectNote] = useState("Item unavailable");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (silent = false) => {
    try {
      const [orderData, callData] = await Promise.all([
        apiFetch<Order[]>("/api/v1/orders?status=PENDING_CONFIRMATION"),
        apiFetch<ServiceCall[]>("/api/v1/service-calls?status=REQUESTED"),
      ]);
      setOrders(orderData);
      setCalls(callData);
      if (!silent) setError(null);
    } catch {
      if (!silent) setError("Could not refresh the queue. Retrying automatically…");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  async function accept(id: string) {
    setBusyId(id);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/orders/${id}/accept`, { method: "POST" });
      setNotice("Order accepted. A dining session and kitchen ticket were created together.");
      await load(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not accept the order.");
    } finally {
      setBusyId(null);
    }
  }

  async function confirmReject() {
    if (!rejecting) return;
    const note = rejectNote.trim();
    if (!note) {
      setError("Explain briefly why the order is rejected — the guest sees this.");
      return;
    }
    setBusyId(rejecting.id);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/orders/${rejecting.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason_code: "UNAVAILABLE", note }),
      });
      setNotice("Order rejected. The guest sees your reason on their status page.");
      setRejecting(null);
      await load(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not reject the order.");
    } finally {
      setBusyId(null);
    }
  }

  async function acknowledge(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/api/v1/service-calls/${id}/acknowledge`, { method: "POST" });
      await load(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not acknowledge the call.");
    } finally {
      setBusyId(null);
    }
  }

  const kitchenCalls = useMemo(() => calls.filter((call) => call.kind === "KITCHEN"), [calls]);
  const guestCalls = useMemo(() => calls.filter((call) => call.kind !== "KITCHEN"), [calls]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Service queue"
        title="Order queue"
        sub="Pending requests are not kitchen tickets. Accepting creates the dining session and kitchen ticket in one transaction, so the kitchen never sees an order the server hasn’t confirmed."
        actions={
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      {kitchenCalls.length > 0 ? (
        <section className="section-card" aria-labelledby="pickup-title">
          <div className="section-card-head">
            <h3 id="pickup-title">Food ready for pickup</h3>
            <span className="badge ready">{kitchenCalls.length}</span>
          </div>
          <div className="section-card-body">
            <div className="grid two">
              {kitchenCalls.map((call) => (
                <article className="card method-card" key={call.id}>
                  <div className="row">
                    <strong>{call.table_display_name}</strong>
                    <StatusBadge status="READY" label="Ready" />
                  </div>
                  {call.ticket_number ? (
                    <p className="muted text-sm" style={{ margin: 0 }}>
                      Ticket {call.ticket_number}
                    </p>
                  ) : null}
                  {call.items_summary ? <p style={{ margin: 0 }}>{call.items_summary}</p> : null}
                  <p className="muted text-sm" style={{ margin: 0 }}>
                    Signalled {minutesAgo(call.requested_at)} · collect at the kitchen pass
                  </p>
                  <button
                    className="btn"
                    disabled={busyId === call.id}
                    onClick={() => void acknowledge(call.id)}
                    type="button"
                  >
                    {busyId === call.id ? "Acknowledging…" : "I’m picking it up"}
                  </button>
                </article>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {guestCalls.length > 0 ? (
        <section className="section-card" aria-labelledby="calls-title">
          <div className="section-card-head">
            <h3 id="calls-title">Waiter calls</h3>
            <span className="badge pending">{guestCalls.length}</span>
          </div>
          <div className="section-card-body">
            <div className="grid two">
              {guestCalls.map((call) => (
                <article className="card method-card" key={call.id}>
                  <div className="row">
                    <strong>{call.table_display_name}</strong>
                    <StatusBadge status="REQUESTED" label="Called" />
                  </div>
                  <p className="muted text-sm" style={{ margin: 0 }}>
                    Requested {minutesAgo(call.requested_at)} · let the table know you’re coming
                  </p>
                  <button
                    className="btn"
                    disabled={busyId === call.id}
                    onClick={() => void acknowledge(call.id)}
                    type="button"
                  >
                    {busyId === call.id ? "Acknowledging…" : "Acknowledge"}
                  </button>
                </article>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section className="section-card" aria-labelledby="pending-title">
        <div className="section-card-head">
          <h3 id="pending-title">Awaiting confirmation</h3>
          <span className="badge pending">{orders.length}</span>
        </div>
        <div className="section-card-body">
          {loading ? <p className="muted">Loading the queue…</p> : null}
          {!loading && orders.length === 0 ? (
            <div className="empty-state">
              <strong>Queue is clear</strong>
              <span>New guest orders appear here within a few seconds.</span>
            </div>
          ) : null}

          <div className="grid two">
            {orders.map((order) => (
              <article className="card method-card" key={order.id}>
                <div className="row">
                  <div>
                    <strong>Guest order</strong>
                    <div className="muted text-sm">
                      Submitted {new Date(order.submitted_at).toLocaleTimeString()} ·{" "}
                      {minutesAgo(order.submitted_at)}
                    </div>
                  </div>
                  <StatusBadge status={order.status} label="Awaiting confirmation" />
                </div>

                <div>
                  {order.items.map((item) => (
                    <div className="order-line" key={item.id}>
                      <span>
                        {item.quantity} × {item.item_name_snapshot}
                        {item.special_instructions ? (
                          <span className="muted text-sm"> · {item.special_instructions}</span>
                        ) : null}
                      </span>
                      <span className="numeric">{formatMoney(item.line_total_minor, item.currency_code)}</span>
                    </div>
                  ))}
                  <div className="order-total">
                    <span>Total</span>
                    <span className="numeric">
                      {formatMoney(order.total_minor, order.items[0]?.currency_code)}
                    </span>
                  </div>
                </div>

                {order.customer_note ? <p className="muted">Guest note: {order.customer_note}</p> : null}

                <div className="page-actions">
                  <button
                    className="btn ok btn-lg"
                    disabled={busyId === order.id}
                    onClick={() => void accept(order.id)}
                    type="button"
                  >
                    {busyId === order.id ? "Working…" : "Accept & send to kitchen"}
                  </button>
                  <button
                    className="btn danger"
                    disabled={busyId === order.id}
                    onClick={() => {
                      setRejecting(order);
                      setRejectNote("Item unavailable");
                      setError(null);
                    }}
                    type="button"
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <Sheet
        open={rejecting !== null}
        onClose={() => setRejecting(null)}
        title="Reject this order?"
        footer={
          <div className="item-sheet-actions">
            <button className="btn secondary" type="button" onClick={() => setRejecting(null)}>
              Keep it pending
            </button>
            <button
              className="btn danger"
              type="button"
              disabled={busyId === rejecting?.id}
              onClick={() => void confirmReject()}
            >
              {busyId === rejecting?.id ? "Rejecting…" : "Reject order"}
            </button>
          </div>
        }
      >
        <p className="muted">
          The guest sees this message on their status page. Nothing is prepared and no bill is created.
        </p>
        <label className="field">
          Reason
          <textarea
            rows={3}
            maxLength={280}
            value={rejectNote}
            data-autofocus
            onChange={(event) => setRejectNote(event.target.value)}
            placeholder="e.g. Sold out for today"
          />
        </label>
      </Sheet>
    </div>
  );
}
