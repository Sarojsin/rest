import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, formatMoney, type PublicOrderStatus } from "../lib/api";

function statusCopy(status: string): { title: string; body: string } {
  if (status === "PENDING_CONFIRMATION") {
    return { title: "Submitted — awaiting staff confirmation", body: "A waiter will review this request before it reaches the kitchen." };
  }
  if (status === "ACCEPTED") {
    return { title: "Accepted — the kitchen has your ticket", body: "Staff confirmed the items. Preparation can now begin." };
  }
  if (status === "REJECTED") {
    return { title: "This request was not accepted", body: "Please ask a waiter if you would like to order something else." };
  }
  if (status === "COMPLETED") {
    return { title: "Served", body: "This order has been completed." };
  }
  return { title: status, body: "" };
}

export default function CustomerStatusPage() {
  const { statusToken } = useParams();
  const [order, setOrder] = useState<PublicOrderStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!statusToken) return;
    let cancelled = false;
    async function load() {
      try {
        const data = await apiFetch<PublicOrderStatus>(`/api/v1/public/orders/${statusToken}`);
        if (!cancelled) setOrder(data);
      } catch {
        if (!cancelled) setError("Status is unavailable.");
      }
    }
    load();
    const timer = window.setInterval(load, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [statusToken]);

  if (error) return <div className="shell"><div className="error">{error}</div></div>;
  if (!order) return <div className="shell">Loading status...</div>;
  const copy = statusCopy(order.status);

  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <div className="mark">HT</div>
          <div>
            <h1>Harbor Table</h1>
            <p>{order.table_display_name}</p>
          </div>
        </Link>
      </header>
      <section className="hero">
        <div className="kicker">{order.table_display_name}</div>
        <h2>{copy.title}</h2>
        <p>{copy.body}</p>
      </section>
      {order.rejection_note ? <div className="error">{order.rejection_note}</div> : null}
      <article className="card">
        {order.items.map((item) => (
          <div className="row" key={`${item.name}-${item.quantity}`}>
            <span>{item.quantity} x {item.name}</span>
            <span>{formatMoney(item.line_total_minor, order.currency_code)}</span>
          </div>
        ))}
        <hr />
        <div className="row">
          <strong>Total</strong>
          <strong>{formatMoney(order.total_minor, order.currency_code)}</strong>
        </div>
      </article>
    </div>
  );
}
