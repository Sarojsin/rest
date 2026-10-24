import { useEffect, useState } from "react";
import { apiFetch, ApiError, type KitchenTicket } from "../../lib/api";
import { useAuth } from "../../lib/auth";

const NEXT: Record<string, string> = {
  NEW: "PREPARING",
  PREPARING: "READY",
  READY: "SERVED",
};

export default function KitchenPage() {
  const { has } = useAuth();
  const [tickets, setTickets] = useState<KitchenTicket[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setTickets(await apiFetch<KitchenTicket[]>("/api/v1/kitchen/tickets"));
  }

  useEffect(() => {
    load().catch(() => setError("Could not load tickets."));
    const timer = window.setInterval(() => {
      load().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  async function advance(itemId: string, status: string) {
    const next = NEXT[status];
    if (!next) return;
    setError(null);
    try {
      await apiFetch(`/api/v1/kitchen/ticket-items/${itemId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: next }),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed.");
    }
  }

  return (
    <div>
      <h2>Kitchen</h2>
      <p className="muted">Tickets appear only after staff acceptance. Status is stored on the server.</p>
      {error ? <div className="error">{error}</div> : null}
      <div className="grid two">
        {tickets.map((ticket) => (
          <article className={`card ticket ${ticket.status}`} key={ticket.id}>
            <div className="row">
              <h3>Ticket {ticket.ticket_number}</h3>
              <span className={`badge ${ticket.status.toLowerCase()}`}>{ticket.status}</span>
            </div>
            <p className="muted">{ticket.table_display_name} · {new Date(ticket.created_at).toLocaleTimeString()}</p>
            {ticket.items.map((item) => (
              <div className="row" key={item.id} style={{ marginTop: 8 }}>
                <div>
                  <strong>{item.quantity_snapshot} x {item.item_name}</strong>
                  {item.instructions_snapshot ? <div className="muted">{item.instructions_snapshot}</div> : null}
                  <div className={`badge ${item.status.toLowerCase()}`}>{item.status}</div>
                </div>
                {has("kitchen.update") && NEXT[item.status] ? (
                  <button className="btn secondary" onClick={() => advance(item.id, item.status)} type="button">
                    Mark {NEXT[item.status].toLowerCase()}
                  </button>
                ) : null}
              </div>
            ))}
          </article>
        ))}
      </div>
      {tickets.length === 0 ? <div className="card">No active tickets.</div> : null}
    </div>
  );
}
