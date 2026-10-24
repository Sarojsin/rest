import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  apiFetch,
  formatMoney,
  newIdempotencyKey,
  ApiError,
  type MenuCategory,
  type MenuItem,
  type Order,
  type Table,
} from "../../lib/api";

type Cart = Record<string, { item: MenuItem; quantity: number }>;

export default function WaiterOrderPage() {
  const { tableId } = useParams();
  const [table, setTable] = useState<Table | null>(null);
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [cart, setCart] = useState<Cart>({});
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey());

  useEffect(() => {
    apiFetch<Table[]>("/api/v1/tables").then((tables) => {
      setTable(tables.find((row) => row.id === tableId) ?? null);
    });
    apiFetch<MenuCategory[]>("/api/v1/menu").then(setCategories);
  }, [tableId]);

  const lines = useMemo(() => Object.values(cart).filter((line) => line.quantity > 0), [cart]);
  const subtotal = lines.reduce((sum, line) => sum + line.item.current_price_minor * line.quantity, 0);

  function setQty(item: MenuItem, quantity: number) {
    setCart((prev) => {
      const next = { ...prev };
      if (quantity <= 0) delete next[item.id];
      else next[item.id] = { item, quantity };
      return next;
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!tableId || lines.length === 0) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const order = await apiFetch<Order>("/api/v1/orders", {
        method: "POST",
        idempotencyKey,
        body: JSON.stringify({
          table_id: tableId,
          customer_note: note,
          items: lines.map((line) => ({ menu_item_id: line.item.id, quantity: line.quantity })),
        }),
      });
      setMessage(`Sent to kitchen. Order ${order.id.slice(0, 8)} is accepted.`);
      setCart({});
      setNote("");
      setIdempotencyKey(newIdempotencyKey());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not send the order.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p><Link to="/staff/tables">Back to floor</Link></p>
      <h2>{table?.display_name ?? "Table"}</h2>
      <p className="muted">Waiter orders are accepted and sent to the kitchen in one authorized action.</p>
      {error ? <div className="error" role="alert">{error}</div> : null}
      {message ? <div className="notice">{message}</div> : null}
      <form onSubmit={submit}>
        {categories.map((category) => (
          <section className="panel" key={category.id} style={{ marginBottom: 16 }}>
            <h3>{category.name}</h3>
            {category.items.filter((item) => item.status === "PUBLISHED").map((item) => {
              const qty = cart[item.id]?.quantity ?? 0;
              return (
                <div className="menu-item" key={item.id}>
                  <div className="thumb">{item.image_emoji || item.name.slice(0, 1)}</div>
                  <div>
                    <strong>{item.name}</strong>
                    <div>{formatMoney(item.current_price_minor, item.currency_code)}</div>
                  </div>
                  <div className="qty">
                    <button type="button" onClick={() => setQty(item, qty - 1)}>-</button>
                    <span>{qty}</span>
                    <button type="button" onClick={() => setQty(item, qty + 1)}>+</button>
                  </div>
                </div>
              );
            })}
          </section>
        ))}
        <label className="field">
          Ticket note
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <div className="row">
          <strong>{formatMoney(subtotal)}</strong>
          <button className="btn" disabled={busy || lines.length === 0} type="submit">
            {busy ? "Sending..." : "Send to kitchen"}
          </button>
        </div>
      </form>
    </div>
  );
}
