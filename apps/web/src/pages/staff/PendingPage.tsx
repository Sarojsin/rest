import { useEffect, useState } from "react";
import { apiFetch, formatMoney, ApiError, type Order } from "../../lib/api";

export default function PendingPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    const data = await apiFetch<Order[]>("/api/v1/orders?status=PENDING_CONFIRMATION");
    setOrders(data);
  }

  useEffect(() => {
    load().catch(() => setError("Could not load the QR queue."));
    const timer = window.setInterval(() => {
      load().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  async function accept(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/api/v1/orders/${id}/accept`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Accept failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function reject(id: string) {
    const note = window.prompt("Rejection reason", "Item unavailable") ?? "";
    if (!note) return;
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/api/v1/orders/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason_code: "UNAVAILABLE", note }),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reject failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h2>QR confirmation queue</h2>
      <p className="muted">Pending requests are not kitchen tickets. Accepting creates the session and ticket atomically.</p>
      {error ? <div className="error">{error}</div> : null}
      {orders.length === 0 ? <div className="card">No pending QR orders.</div> : null}
      <div className="grid two">
        {orders.map((order) => (
          <article className="card" key={order.id}>
            <div className="row">
              <strong>Submitted {new Date(order.submitted_at).toLocaleTimeString()}</strong>
              <span className="badge pending">Awaiting confirmation</span>
            </div>
            {order.items.map((item) => (
              <div className="row" key={item.id}>
                <span>{item.quantity} x {item.item_name_snapshot}</span>
                <span>{formatMoney(item.line_total_minor, item.currency_code)}</span>
              </div>
            ))}
            {order.customer_note ? <p className="muted">Note: {order.customer_note}</p> : null}
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn ok" disabled={busyId === order.id} onClick={() => accept(order.id)} type="button">Accept</button>
              <button className="btn warn" disabled={busyId === order.id} onClick={() => reject(order.id)} type="button">Reject</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
