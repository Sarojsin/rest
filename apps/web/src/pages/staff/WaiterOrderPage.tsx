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
import { StatusBadge } from "../../components/StatusBadge";

type Cart = Record<string, { item: MenuItem; quantity: number }>;

export default function WaiterOrderPage() {
  const { tableId } = useParams();
  const [table, setTable] = useState<Table | null>(null);
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [cart, setCart] = useState<Cart>({});
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey());

  useEffect(() => {
    let cancelled = false;
    Promise.all([apiFetch<Table[]>("/api/v1/tables"), apiFetch<MenuCategory[]>("/api/v1/menu")])
      .then(([tables, menu]) => {
        if (cancelled) return;
        setTable(tables.find((row) => row.id === tableId) ?? null);
        setCategories(menu);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load the table or the menu.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tableId]);

  const lines = useMemo(() => Object.values(cart).filter((line) => line.quantity > 0), [cart]);
  const subtotal = lines.reduce((sum, line) => sum + line.item.current_price_minor * line.quantity, 0);
  const currency =
    lines[0]?.item.currency_code ??
    categories.flatMap((category) => category.items)[0]?.currency_code ??
    "USD";
  const itemCount = lines.reduce((total, line) => total + line.quantity, 0);

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
      setMessage(`Sent to the kitchen — order ${order.id.slice(0, 8)} is accepted and ticketed.`);
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
    <div className="page">
      <div className="page-header">
        <div>
          <p className="kicker">
            <Link to="/staff/tables">Floor</Link> · New order
          </p>
          <h1 className="page-title">{table?.display_name ?? "Table"}</h1>
          <p className="page-sub">
            Waiter orders are accepted and sent to the kitchen in one authorised action. Prices come from
            the server catalog.
            {table ? (
              <span>
                {" "}
                <StatusBadge status={table.occupancy} />
              </span>
            ) : null}
          </p>
        </div>
      </div>

      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <div className="notice">{message}</div> : null}
      {loading ? <p className="muted">Loading menu…</p> : null}

      <form onSubmit={submit} className="order-layout">
        <div className="stack">
          {categories
            .filter((category) => category.items.some((item) => item.status === "PUBLISHED"))
            .map((category) => (
              <section className="menu-category" key={category.id} aria-labelledby={`wo-${category.id}`}>
                <div className="menu-category-head">
                  <h3 id={`wo-${category.id}`}>{category.name}</h3>
                  <span className="muted text-sm">
                    {category.items.filter((item) => item.status === "PUBLISHED").length} available
                  </span>
                </div>
                {category.items
                  .filter((item) => item.status === "PUBLISHED")
                  .map((item) => {
                    const qty = cart[item.id]?.quantity ?? 0;
                    return (
                      <div className="order-row" key={item.id}>
                        <div className="menu-row-main">
                          <strong>{item.name}</strong>
                          <div className="muted">{item.description || "No description"}</div>
                        </div>
                        <span className="menu-row-price">
                          {formatMoney(item.current_price_minor, item.currency_code)}
                        </span>
                        <div className="qty">
                          <button
                            type="button"
                            aria-label={`Remove one ${item.name}`}
                            onClick={() => setQty(item, qty - 1)}
                            disabled={qty === 0}
                          >
                            −
                          </button>
                          <span aria-live="polite">{qty}</span>
                          <button
                            type="button"
                            aria-label={`Add one ${item.name}`}
                            onClick={() => setQty(item, qty + 1)}
                          >
                            +
                          </button>
                        </div>
                      </div>
                    );
                  })}
              </section>
            ))}

          {!loading && categories.length === 0 ? (
            <div className="empty-state">
              <strong>No menu items</strong>
              <span>Publish items under Menu before taking orders.</span>
            </div>
          ) : null}
        </div>

        <aside className="order-summary" aria-label="Order summary">
          <h3>Order summary</h3>
          {lines.length === 0 ? (
            <p className="muted">Nothing selected yet. Add items from the menu.</p>
          ) : (
            lines.map((line) => (
              <div className="order-line" key={line.item.id}>
                <span>
                  {line.quantity} × {line.item.name}
                </span>
                <span className="numeric">
                  {formatMoney(line.item.current_price_minor * line.quantity, line.item.currency_code)}
                </span>
              </div>
            ))
          )}

          <label className="field" style={{ marginTop: "var(--space-3)" }}>
            Ticket note
            <input
              value={note}
              maxLength={280}
              onChange={(event) => setNote(event.target.value)}
              placeholder="e.g. One plate to share, no chilli"
            />
          </label>

          <div className="order-total">
            <span>
              Subtotal{itemCount > 0 ? ` · ${itemCount} item${itemCount === 1 ? "" : "s"}` : ""}
            </span>
            <span className="numeric">{formatMoney(subtotal, currency)}</span>
          </div>
          <p className="hint">Tax and totals are calculated by the server when the order is accepted.</p>

          <button
            className="btn btn-lg btn-block"
            disabled={busy || lines.length === 0}
            type="submit"
            style={{ marginTop: "var(--space-3)" }}
          >
            {busy ? "Sending…" : "Send to kitchen"}
          </button>

          {message ? (
            <Link className="btn secondary btn-block" to="/staff/tables" style={{ marginTop: "var(--space-2)" }}>
              Back to floor
            </Link>
          ) : null}
        </aside>
      </form>
    </div>
  );
}
