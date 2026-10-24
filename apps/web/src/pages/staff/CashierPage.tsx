import { useEffect, useState } from "react";
import {
  apiFetch,
  formatMoney,
  newIdempotencyKey,
  ApiError,
  type Bill,
  type Table,
} from "../../lib/api";

export default function CashierPage() {
  const [tables, setTables] = useState<Table[]>([]);
  const [selected, setSelected] = useState<Table | null>(null);
  const [bill, setBill] = useState<Bill | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadTables() {
    setTables(await apiFetch<Table[]>("/api/v1/tables"));
  }

  useEffect(() => {
    loadTables().catch(() => setError("Could not load tables."));
  }, []);

  async function openSession(table: Table) {
    setSelected(table);
    setBill(null);
    setError(null);
    setMessage(null);
    if (!table.active_session_id) {
      setError("This table has no open dining session.");
      return;
    }
    try {
      const existing = await apiFetch<Bill>(`/api/v1/sessions/${table.active_session_id}/bill`);
      setBill(existing);
    } catch {
      setBill(null);
    }
  }

  async function issue() {
    if (!selected?.active_session_id) return;
    setBusy(true);
    setError(null);
    try {
      const issued = await apiFetch<Bill>(`/api/v1/sessions/${selected.active_session_id}/bill/issue`, {
        method: "POST",
      });
      setBill(issued);
      setMessage("Bill issued from accepted items. Totals are calculated on the server.");
      await loadTables();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not issue bill.");
    } finally {
      setBusy(false);
    }
  }

  async function pay() {
    if (!bill) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<Bill>(`/api/v1/bills/${bill.id}/cash-payments`, {
        method: "POST",
        idempotencyKey: newIdempotencyKey(),
        body: JSON.stringify({ amount_minor: bill.balance_due_minor }),
      });
      setBill(updated);
      setMessage(updated.status === "PAID" ? "Bill settled and session closed." : "Partial payment recorded.");
      await loadTables();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Payment failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2>Cashier</h2>
      <p className="muted">Online payment is not confirmed by a browser redirect. Cash settlement is recorded by authorized staff.</p>
      {error ? <div className="error">{error}</div> : null}
      {message ? <div className="notice">{message}</div> : null}
      <div className="grid two">
        <section>
          <div className="grid tables">
            {tables.map((table) => (
              <button
                key={table.id}
                className={`card table-tile ${table.occupancy}`}
                onClick={() => openSession(table)}
                type="button"
              >
                <strong>{table.display_name}</strong>
                <span className={`badge ${table.occupancy.toLowerCase()}`}>{table.occupancy}</span>
              </button>
            ))}
          </div>
        </section>
        <section className="card">
          {!selected ? <p>Select a table.</p> : null}
          {selected && !bill ? (
            <div>
              <h3>{selected.display_name}</h3>
              <p className="muted">Issue a bill from accepted session items.</p>
              <button className="btn" disabled={busy || !selected.active_session_id} onClick={issue} type="button">
                Issue bill
              </button>
            </div>
          ) : null}
          {bill ? (
            <div>
              <div className="row">
                <h3>Bill</h3>
                <span className={`badge ${bill.status.toLowerCase()}`}>{bill.status}</span>
              </div>
              {bill.items.map((item) => (
                <div className="row" key={item.id}>
                  <span>{item.quantity} x {item.description_snapshot}</span>
                  <span>{formatMoney(item.line_total_minor, bill.currency_code)}</span>
                </div>
              ))}
              <hr />
              <div className="row"><span>Subtotal</span><span>{formatMoney(bill.subtotal_minor, bill.currency_code)}</span></div>
              <div className="row"><span>Tax</span><span>{formatMoney(bill.tax_minor, bill.currency_code)}</span></div>
              <div className="row"><strong>Total</strong><strong>{formatMoney(bill.total_minor, bill.currency_code)}</strong></div>
              <div className="row"><span>Paid</span><span>{formatMoney(bill.paid_minor, bill.currency_code)}</span></div>
              <div className="row"><strong>Due</strong><strong>{formatMoney(bill.balance_due_minor, bill.currency_code)}</strong></div>
              {bill.status !== "PAID" ? (
                <div className="row" style={{ marginTop: 16 }}>
                  <button className="btn secondary" disabled={busy} onClick={issue} type="button">Reissue</button>
                  <button className="btn ok" disabled={busy || bill.balance_due_minor <= 0} onClick={pay} type="button">
                    Record cash due
                  </button>
                </div>
              ) : <p className="notice">Settled.</p>}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
