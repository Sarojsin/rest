import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, ApiError, formatMoney, type PublicOrderStatus } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";

function statusCopy(status: string): { title: string; body: string } {
  if (status === "PENDING_CONFIRMATION") {
    return {
      title: "Submitted — awaiting staff confirmation",
      body: "A waiter will review this request before it reaches the kitchen. Nothing is being prepared yet.",
    };
  }
  if (status === "ACCEPTED") {
    return {
      title: "Confirmed — the kitchen has your ticket",
      body: "Staff accepted your order. The kitchen is working on it; a waiter will serve you at the table.",
    };
  }
  if (status === "REJECTED") {
    return {
      title: "This request was not accepted",
      body: "Please ask a waiter if you would like to order something else.",
    };
  }
  if (status === "COMPLETED") {
    return { title: "Served", body: "This order has been completed. We hope you enjoyed it." };
  }
  if (status === "CANCELLED") {
    return { title: "Cancelled", body: "This order has been cancelled." };
  }
  return { title: status, body: "" };
}

type PublicBill = {
  bill_id: string;
  status: string;
  currency_code: string;
  subtotal_minor: number;
  tax_minor: number;
  total_minor: number;
  paid_minor: number;
  balance_due_minor: number;
  items: {
    name: string;
    quantity: number;
    unit_price_minor: number;
    line_total_minor: number;
    currency_code: string;
  }[];
  payments: { id: string; method: string; status: string; amount_minor: number }[];
};

type Step = { key: string; title: string; detail: string };

function timelineFor(order: PublicOrderStatus): Step[] {
  const steps: Step[] = [
    {
      key: "submitted",
      title: "Submitted",
      detail: new Date(order.submitted_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    },
    {
      key: "confirmed",
      title: "Confirmed by staff",
      detail: order.accepted_at
        ? new Date(order.accepted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : "Waiting for a waiter",
    },
    {
      key: "served",
      title: "Served",
      detail: order.status === "COMPLETED" ? "Order complete" : "Once the kitchen finishes",
    },
  ];
  return steps;
}

function stepState(order: PublicOrderStatus, key: string): "done" | "current" | "todo" {
  if (order.status === "REJECTED" || order.status === "CANCELLED") {
    return key === "submitted" ? "done" : "todo";
  }
  if (key === "submitted") return "done";
  if (key === "confirmed") {
    if (order.accepted_at) return "done";
    return order.status === "PENDING_CONFIRMATION" ? "current" : "todo";
  }
  if (order.status === "COMPLETED") return "done";
  return order.status === "ACCEPTED" ? "current" : "todo";
}

export default function CustomerStatusPage() {
  const { statusToken } = useParams();
  const [order, setOrder] = useState<PublicOrderStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [bill, setBill] = useState<PublicBill | null>(null);
  const [billError, setBillError] = useState<string | null>(null);
  const [billLoading, setBillLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [rated, setRated] = useState(false);

  const load = useCallback(async () => {
    if (!statusToken) return;
    try {
      const data = await apiFetch<PublicOrderStatus>(`/api/v1/public/orders/${statusToken}`);
      setOrder(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Status is unavailable.");
    }
  }, [statusToken]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function loadBill() {
    if (!statusToken) return;
    setBillError(null);
    setBillLoading(true);
    try {
      const data = await apiFetch<PublicBill>(`/api/v1/public/orders/${statusToken}/bill`);
      setBill(data);
    } catch (err) {
      setBillError(
        err instanceof ApiError
          ? err.detail
          : "The bill is not available yet. It appears after staff issue it at the cashier."
      );
    } finally {
      setBillLoading(false);
    }
  }

  async function cancelOrder() {
    if (!statusToken) return;
    setCancelling(true);
    setActionError(null);
    try {
      await apiFetch(`/api/v1/public/orders/${statusToken}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: "Customer request" }),
      });
      setConfirmCancel(false);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : "This order cannot be cancelled now.");
    } finally {
      setCancelling(false);
    }
  }

  async function submitRating() {
    if (!statusToken || rating < 1) return;
    setActionError(null);
    try {
      await apiFetch(`/api/v1/public/orders/${statusToken}/rate`, {
        method: "POST",
        body: JSON.stringify({ rating, comment }),
      });
      setRated(true);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : "Could not submit your rating.");
    }
  }

  if (error && !order) {
    return (
      <div className="menu-shell" data-theme="customer">
        <div className="shell">
          <div className="error" role="alert">
            {error}
          </div>
          <Link className="btn secondary" to="/">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="menu-shell" data-theme="customer">
        <div className="shell">
          <p className="muted">Loading your order…</p>
        </div>
      </div>
    );
  }

  const copy = statusCopy(order.status);
  const canCancel = order.status === "PENDING_CONFIRMATION" || order.status === "ACCEPTED";
  const canRate = order.status === "COMPLETED" || order.status === "ACCEPTED";

  return (
    <div className="menu-shell" data-theme="customer">
      <div className="shell page">
        <header className="topbar">
          <Link className="brand" to="/">
            <div className="mark">HT</div>
            <div>
              <h1>Harbor Table</h1>
              <p>{order.table_display_name}</p>
            </div>
          </Link>
          <StatusBadge status={order.status} />
        </header>

        {error ? (
          <div className="warning-banner" role="status">
            {error} Showing the last confirmed state.
          </div>
        ) : null}

        <section className="status-hero">
          <p className="kicker">{order.table_display_name}</p>
          <h2>{copy.title}</h2>
          <p>{copy.body}</p>

          <ol className="timeline" aria-label="Order progress">
            {timelineFor(order).map((step, index) => {
              const state = stepState(order, step.key);
              return (
                <li
                  className={`timeline-step ${state === "done" ? "is-done" : ""} ${
                    state === "current" ? "is-current" : ""
                  }`}
                  key={step.key}
                >
                  <span className="timeline-dot" aria-hidden="true">
                    {state === "done" ? "✓" : index + 1}
                  </span>
                  <div className="timeline-body">
                    <strong>{step.title}</strong>
                    <span>{step.detail}</span>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        {order.status === "REJECTED" ? (
          <div className="error" role="alert">
            <strong>Not accepted.</strong>{" "}
            {order.rejection_note || "Please speak to a waiter to order something else."}
          </div>
        ) : null}

        {actionError ? (
          <div className="error" role="alert">
            {actionError}
          </div>
        ) : null}

        <section className="status-card" aria-labelledby="order-lines-title">
          <h3 id="order-lines-title">Your order</h3>
          {order.items.map((item, index) => (
            <div className="status-line" key={`${item.name}-${index}`}>
              <span>
                {item.quantity} × {item.name}
              </span>
              <span className="numeric">{formatMoney(item.line_total_minor, order.currency_code)}</span>
            </div>
          ))}
          <div className="status-line total">
            <span>Total</span>
            <span className="numeric">{formatMoney(order.total_minor, order.currency_code)}</span>
          </div>
          <p className="hint">
            Tax and totals are calculated by the restaurant. The figure above is the recorded total for
            this order.
          </p>
        </section>

        {canCancel ? (
          <section className="status-card">
            <h3>Need to change something?</h3>
            <p className="muted text-sm">
              Cancelling is only possible while the order is pending or confirmed. After that, please ask
              a waiter.
            </p>
            {confirmCancel ? (
              <div className="page-actions">
                <button
                  className="btn danger"
                  type="button"
                  disabled={cancelling}
                  onClick={() => void cancelOrder()}
                >
                  {cancelling ? "Cancelling…" : "Yes, cancel this order"}
                </button>
                <button
                  className="btn secondary"
                  type="button"
                  disabled={cancelling}
                  onClick={() => setConfirmCancel(false)}
                >
                  Keep my order
                </button>
              </div>
            ) : (
              <button className="btn ghost" type="button" onClick={() => setConfirmCancel(true)}>
                Cancel order
              </button>
            )}
          </section>
        ) : null}

        <section className="status-card">
          <div className="row" style={{ marginBottom: "var(--space-2)" }}>
            <h3 style={{ margin: 0 }}>Bill</h3>
            <button className="btn secondary btn-sm" type="button" onClick={() => void loadBill()}>
              {billLoading ? "Checking…" : bill ? "Refresh bill" : "View bill"}
            </button>
          </div>
          {billError ? (
            <p className="hint" role="status">
              {billError}
            </p>
          ) : null}
          {bill ? (
            <div>
              <div className="row" style={{ marginBottom: "var(--space-2)" }}>
                <StatusBadge status={bill.status} />
                <span className="muted text-sm">Issued at the cashier</span>
              </div>
              {bill.items.map((item, index) => (
                <div className="status-line" key={`${item.name}-${index}`}>
                  <span>
                    {item.quantity} × {item.name}
                  </span>
                  <span className="numeric">{formatMoney(item.line_total_minor, bill.currency_code)}</span>
                </div>
              ))}
              <div className="status-line">
                <span>Subtotal</span>
                <span className="numeric">{formatMoney(bill.subtotal_minor, bill.currency_code)}</span>
              </div>
              <div className="status-line">
                <span>Tax</span>
                <span className="numeric">{formatMoney(bill.tax_minor, bill.currency_code)}</span>
              </div>
              <div className="status-line">
                <span>Paid</span>
                <span className="numeric">{formatMoney(bill.paid_minor, bill.currency_code)}</span>
              </div>
              <div className="status-line total">
                <span>Balance due</span>
                <span className="numeric">{formatMoney(bill.balance_due_minor, bill.currency_code)}</span>
              </div>
              <p className="hint">
                {bill.balance_due_minor > 0
                  ? "To pay, please ask staff at the cashier. The bill is marked paid only after staff confirm the payment."
                  : "This bill is settled. Thank you."}
              </p>
            </div>
          ) : null}
        </section>

        {canRate && !rated ? (
          <section className="status-card">
            <h3>Rate your food</h3>
            <div className="rating" role="group" aria-label="Rating out of five">
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={value <= rating}
                  aria-label={`${value} star${value === 1 ? "" : "s"}`}
                  onClick={() => setRating(value)}
                >
                  {value <= rating ? "★" : "☆"}
                </button>
              ))}
            </div>
            <label className="field" style={{ marginTop: "var(--space-3)" }}>
              Comment (optional)
              <textarea
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="What worked, what didn’t"
                maxLength={280}
                rows={3}
              />
            </label>
            <button className="btn" type="button" disabled={rating < 1} onClick={() => void submitRating()}>
              Submit rating
            </button>
          </section>
        ) : null}

        {rated ? (
          <div className="notice" role="status">
            Thanks for your rating — it helps the restaurant improve.
          </div>
        ) : null}

        <p className="hint">
          Keep this page open to see updates. Only this order is visible from this link.
        </p>
      </div>
    </div>
  );
}
