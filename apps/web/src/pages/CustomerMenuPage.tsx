import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  apiFetch,
  formatMoney,
  newIdempotencyKey,
  ApiError,
  type MenuItem,
  type PublicMenu,
} from "../lib/api";

type Cart = Record<string, { item: MenuItem; quantity: number; note: string }>;

export default function CustomerMenuPage() {
  const { qrToken } = useParams();
  const navigate = useNavigate();
  const [menu, setMenu] = useState<PublicMenu | null>(null);
  const [cart, setCart] = useState<Cart>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [idempotencyKey] = useState(() => newIdempotencyKey());

  useEffect(() => {
    if (!qrToken) return;
    apiFetch<PublicMenu>(`/api/v1/public/qr/${qrToken}/menu`)
      .then(setMenu)
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Menu unavailable."));
  }, [qrToken]);

  const lines = useMemo(() => Object.values(cart).filter((line) => line.quantity > 0), [cart]);
  const subtotal = lines.reduce((sum, line) => sum + line.item.current_price_minor * line.quantity, 0);

  function setQty(item: MenuItem, quantity: number) {
    setCart((prev) => {
      const next = { ...prev };
      if (quantity <= 0) delete next[item.id];
      else next[item.id] = { item, quantity, note: next[item.id]?.note ?? "" };
      return next;
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!qrToken || lines.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await apiFetch<{ order: { id: string }; status_token: string }>(
        `/api/v1/public/qr/${qrToken}/orders`,
        {
          method: "POST",
          idempotencyKey,
          body: JSON.stringify({
            customer_note: note,
            items: lines.map((line) => ({
              menu_item_id: line.item.id,
              quantity: line.quantity,
              special_instructions: line.note,
            })),
          }),
        }
      );
      navigate(`/status/${result.status_token}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not submit the order.");
    } finally {
      setBusy(false);
    }
  }

  if (!menu && !error) return <div className="shell">Loading menu...</div>;
  if (error && !menu) {
    return (
      <div className="shell">
        <div className="error" role="alert">{error}</div>
        <Link to="/">Back</Link>
      </div>
    );
  }
  if (!menu) return null;

  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <div className="mark">HT</div>
          <div>
            <h1>{menu.restaurant_name}</h1>
            <p>{menu.table_display_name}</p>
          </div>
        </Link>
      </header>
      <section className="hero">
        <div className="kicker">{menu.table_display_name}</div>
        <h2>Order from the table.</h2>
        <p>Your request is sent to staff first. Food is not prepared until a waiter accepts it.</p>
      </section>
      {error ? <div className="error" role="alert">{error}</div> : null}
      <form onSubmit={submit}>
        {menu.categories.map((category) => (
          <section className="panel" key={category.id} style={{ marginBottom: 16 }}>
            <h3>{category.name}</h3>
            <p className="muted">{category.description}</p>
            {category.items.map((item) => {
              const qty = cart[item.id]?.quantity ?? 0;
              return (
                <div className="menu-item" key={item.id}>
                  <div className="thumb" aria-hidden>{item.image_emoji || item.name.slice(0, 1)}</div>
                  <div>
                    <strong>{item.name}</strong>
                    <div className="muted">{item.description}</div>
                    <div>{formatMoney(item.current_price_minor, item.currency_code)}</div>
                  </div>
                  <div className="qty">
                    <button type="button" onClick={() => setQty(item, qty - 1)} aria-label={`Remove ${item.name}`}>-</button>
                    <span>{qty}</span>
                    <button type="button" onClick={() => setQty(item, qty + 1)} aria-label={`Add ${item.name}`}>+</button>
                  </div>
                </div>
              );
            })}
          </section>
        ))}
        <label className="field">
          Note for the kitchen
          <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={280} rows={3} />
        </label>
        <div className="cart">
          <div>
            <div className="muted">{lines.length} item{lines.length === 1 ? "" : "s"}</div>
            <strong>{formatMoney(subtotal, menu.currency_code)}</strong>
            <div className="muted">Tax is calculated by the restaurant when staff confirm.</div>
          </div>
          <button className="btn" disabled={busy || lines.length === 0} type="submit">
            {busy ? "Sending..." : "Send to staff"}
          </button>
        </div>
      </form>
    </div>
  );
}
