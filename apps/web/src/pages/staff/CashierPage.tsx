import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiFetch,
  formatMoney,
  getToken,
  newIdempotencyKey,
  ApiError,
  type Bill,
  type PaymentMethodConfig,
  type Table,
} from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";

type PaymentState = "UNPAID" | "PENDING" | "PAID";

const STATE_LABEL: Record<PaymentState, string> = {
  UNPAID: "Unpaid",
  PENDING: "Verification pending",
  PAID: "Paid",
};

export default function CashierPage() {
  const [tables, setTables] = useState<Table[]>([]);
  const [methods, setMethods] = useState<PaymentMethodConfig[]>([]);
  const [selected, setSelected] = useState<Table | null>(null);
  const [bill, setBill] = useState<Bill | null>(null);
  const [chosenMethod, setChosenMethod] = useState<PaymentMethodConfig | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingBill, setLoadingBill] = useState(false);

  const loadTables = useCallback(async () => {
    const data = await apiFetch<Table[]>("/api/v1/tables");
    setTables(data);
    return data;
  }, []);

  const loadMethods = useCallback(async () => {
    const all = await apiFetch<PaymentMethodConfig[]>("/api/v1/payment-methods");
    setMethods(all.filter((method) => method.is_active || method.kind === "CASH"));
  }, []);

  useEffect(() => {
    loadTables().catch(() => setError("Could not load tables."));
    loadMethods().catch(() => setError("Could not load payment methods."));
  }, [loadTables, loadMethods]);

  // Expire the checkout panel whenever the table or bill changes.
  useEffect(() => {
    setChosenMethod(null);
    setQrUrl(null);
    setVerified(false);
  }, [selected, bill?.version]);

  // Fetch the QR image as an authenticated blob (img tags cannot send headers).
  useEffect(() => {
    if (!chosenMethod || chosenMethod.kind !== "QR" || !chosenMethod.qr_image_url) {
      setQrUrl(null);
      return;
    }
    let cancelled = false;
    let created: string | null = null;
    setQrUrl(null);
    async function load() {
      try {
        const response = await fetch(chosenMethod!.qr_image_url!, {
          headers: { Authorization: `Bearer ${getToken() ?? ""}` },
        });
        if (!response.ok) throw new Error("QR image request failed");
        const blob = await response.blob();
        created = URL.createObjectURL(blob);
        if (!cancelled) setQrUrl(created);
      } catch {
        if (!cancelled) setError("Could not load the QR image. Try again.");
      }
    }
    void load();
    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [chosenMethod]);

  async function openSession(table: Table) {
    setSelected(table);
    setChosenMethod(null);
    setVerified(false);
    setQrUrl(null);
    setError(null);
    setMessage(null);
    setBill(null);
    if (!table.active_session_id) {
      setError("This table has no open dining session yet. Seating happens when a guest order is confirmed.");
      return;
    }
    setLoadingBill(true);
    try {
      const existing = await apiFetch<Bill>(`/api/v1/sessions/${table.active_session_id}/bill`);
      setBill(existing);
    } catch {
      setBill(null);
    } finally {
      setLoadingBill(false);
    }
  }

  async function issue() {
    if (!selected?.active_session_id) return;
    setBusy(true);
    setError(null);
    setMessage(null);
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

  const usableMethods = useMemo(
    () => methods.filter((method) => method.is_active && (method.kind === "CASH" || method.has_qr_image)),
    [methods]
  );

  // Active QR methods without an uploaded image cannot be offered: the cashier
  // has no code to show the guest. Surface that instead of silently hiding them.
  const unusableQrMethods = useMemo(
    () => methods.filter((method) => method.is_active && method.kind === "QR" && !method.has_qr_image),
    [methods]
  );

  async function verifyAndRecord() {
    if (!bill || !chosenMethod || !verified) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await apiFetch<Bill>(`/api/v1/bills/${bill.id}/payments`, {
        method: "POST",
        idempotencyKey: newIdempotencyKey(),
        body: JSON.stringify({
          method_id: chosenMethod.id,
          amount_minor: bill.balance_due_minor,
        }),
      });
      setBill(updated);
      setMessage(
        updated.status === "PAID"
          ? `Payment verified via ${chosenMethod.label}. Bill settled and session closed.`
          : `Payment verified via ${chosenMethod.label}. Partial payment recorded.`
      );
      setChosenMethod(null);
      setVerified(false);
      setQrUrl(null);
      await loadTables();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not record the payment.");
    } finally {
      setBusy(false);
    }
  }

  const payable = Boolean(bill && (bill.status === "ISSUED" || bill.status === "PARTIALLY_PAID"));
  const paymentState: PaymentState =
    bill?.status === "PAID" || bill?.status === "VOID"
      ? "PAID"
      : chosenMethod && verified
        ? "PENDING"
        : "UNPAID";

  const occupiedCount = tables.filter((table) => table.occupancy !== "AVAILABLE").length;

  return (
    <>
      <div className="ops-page-head">
        <div>
          <h1>Cashier</h1>
          <p>
            Showing a payment QR only gives the guest a way to pay. A bill becomes paid only after you
            confirm the money arrived. {occupiedCount} table{occupiedCount === 1 ? "" : "s"} in service.
          </p>
        </div>
        <div className="page-actions">
          <button
            className="btn secondary"
            type="button"
            onClick={() => {
              void loadTables().catch(() => setError("Could not refresh tables."));
              void loadMethods().catch(() => undefined);
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {error ? <div className="error no-print">{error}</div> : null}
      {message ? <div className="notice no-print">{message}</div> : null}

      <div className="checkout-layout">
        <section aria-label="Tables">
          <div className="checkout-tables">
            {tables.map((table) => (
              <button
                key={table.id}
                type="button"
                className={`checkout-table ${table.occupancy} ${
                  selected?.id === table.id ? "is-selected" : ""
                }`}
                aria-pressed={selected?.id === table.id}
                onClick={() => void openSession(table)}
              >
                <strong>{table.display_name}</strong>
                <StatusBadge status={table.occupancy} />
                {table.pending_qr_count > 0 ? (
                  <span className="muted text-sm">{table.pending_qr_count} awaiting confirmation</span>
                ) : null}
              </button>
            ))}
            {tables.length === 0 ? <p className="muted">No tables configured.</p> : null}
          </div>
        </section>

        <section className="checkout-panel" aria-live="polite">
          {!selected ? (
            <div className="empty-state">
              <strong>Select a table</strong>
              <span>Pick a table on the left to issue or settle its bill.</span>
            </div>
          ) : null}

          {selected && loadingBill ? <p className="muted">Loading bill for {selected.display_name}…</p> : null}

          {selected && !bill && !loadingBill ? (
            <div>
              <div className="row" style={{ marginBottom: "var(--space-3)" }}>
                <h2 style={{ margin: 0 }}>{selected.display_name}</h2>
                <StatusBadge status={selected.occupancy} />
              </div>
              <p className="muted">
                A bill is built from accepted items only. The server calculates tax and totals, so the
                figure here is final once issued.
              </p>
              {selected.active_session_id ? (
                <button className="btn btn-lg" type="button" disabled={busy} onClick={() => void issue()}>
                  {busy ? "Issuing…" : "Issue bill"}
                </button>
              ) : (
                <div className="warning-banner">
                  No open dining session. Seat the table by confirming a guest order first.
                </div>
              )}
            </div>
          ) : null}

          {selected && bill ? (
            <div>
              <div className="row" style={{ marginBottom: "var(--space-3)" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{selected.display_name}</h2>
                  <p className="muted text-sm" style={{ margin: 0 }}>
                    Bill {bill.id.slice(0, 8)} · {bill.items.length} line
                    {bill.items.length === 1 ? "" : "s"}
                  </p>
                </div>
                <span
                  className={`payment-state ${
                    paymentState === "PAID" ? "is-paid" : paymentState === "PENDING" ? "is-pending" : "is-unpaid"
                  }`}
                >
                  {STATE_LABEL[paymentState]}
                </span>
              </div>

              <div className="table-scroll" style={{ marginBottom: "var(--space-3)" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th className="num">Qty</th>
                      <th className="num">Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bill.items.map((item) => (
                      <tr key={item.id}>
                        <td>
                          {item.description_snapshot}
                          {item.tax_minor > 0 ? (
                            <span className="muted text-sm"> · tax {formatMoney(item.tax_minor, bill.currency_code)}</span>
                          ) : null}
                        </td>
                        <td className="num">{item.quantity}</td>
                        <td className="num">{formatMoney(item.line_total_minor, bill.currency_code)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="bill-line">
                <span className="muted">Subtotal</span>
                <span>{formatMoney(bill.subtotal_minor, bill.currency_code)}</span>
              </div>
              <div className="bill-line">
                <span className="muted">Tax</span>
                <span>{formatMoney(bill.tax_minor, bill.currency_code)}</span>
              </div>
              {bill.paid_minor > 0 ? (
                <div className="bill-line">
                  <span className="muted">Already paid</span>
                  <span>−{formatMoney(bill.paid_minor, bill.currency_code)}</span>
                </div>
              ) : null}
              <div className="bill-line total">
                <span>Balance due</span>
                <span>{formatMoney(bill.balance_due_minor, bill.currency_code)}</span>
              </div>

              {bill.payments.length > 0 ? (
                <details style={{ marginTop: "var(--space-3)" }}>
                  <summary className="muted text-sm" style={{ cursor: "pointer" }}>
                    Recorded payments ({bill.payments.length})
                  </summary>
                  <div style={{ marginTop: "var(--space-2)" }}>
                    {bill.payments.map((payment) => (
                      <div className="bill-line" key={payment.id}>
                        <span>
                          {payment.method}
                          {payment.note ? ` · ${payment.note}` : ""}
                          {payment.succeeded_at ? (
                            <span className="muted text-sm">
                              {" "}
                              · {new Date(payment.succeeded_at).toLocaleString()}
                            </span>
                          ) : null}
                        </span>
                        <span>{formatMoney(payment.amount_minor, bill.currency_code)}</span>
                      </div>
                    ))}
                  </div>
                </details>
              ) : null}

              {bill.status === "PAID" ? (
                <div className="notice" style={{ marginTop: "var(--space-4)" }}>
                  Settled. The session is closed and the table is free for the next guest.
                </div>
              ) : null}

              {bill.status === "VOID" ? (
                <div className="warning-banner" style={{ marginTop: "var(--space-4)" }}>
                  This bill was voided. Issue a new bill if the table is still in service.
                </div>
              ) : null}

              {payable ? (
                <div className="checkout">
                  <h3>Take payment</h3>
                  <div className="method-picker" role="group" aria-label="Payment method">
                    {usableMethods.map((method) => (
                      <button
                        key={method.id}
                        className={`btn secondary method-choice ${
                          chosenMethod?.id === method.id ? "active" : ""
                        }`}
                        aria-pressed={chosenMethod?.id === method.id}
                        disabled={busy}
                        onClick={() => {
                          setChosenMethod(method);
                          setVerified(false);
                        }}
                        type="button"
                      >
                        {method.label}
                        {method.kind === "QR" ? <span className="badge">QR</span> : null}
                      </button>
                    ))}
                    {usableMethods.length === 0 ? (
                      <p className="hint">
                        No usable payment methods. Ask the owner to add one under Payment methods.
                      </p>
                    ) : null}
                  </div>

                  {unusableQrMethods.length > 0 ? (
                    <p className="hint">
                      {unusableQrMethods.map((method) => method.label).join(", ")}{" "}
                      {unusableQrMethods.length === 1 ? "is" : "are"} hidden until a QR image is
                      uploaded under Payment methods.
                    </p>
                  ) : null}

                  {chosenMethod?.kind === "QR" ? (
                    <div className="qr-panel">
                      <div className="qr-warning">
                        Show this code to the guest — <strong>not yet paid</strong>
                      </div>
                      {qrUrl ? (
                        <img
                          className="qr-customer"
                          src={qrUrl}
                          alt={`${chosenMethod.label} payment QR code`}
                          width={260}
                          height={260}
                        />
                      ) : (
                        <p className="hint">Loading QR image…</p>
                      )}
                      <div className="bill-summary" style={{ position: "static", marginTop: 0 }}>
                        <span className="bill-summary-label">Amount due</span>
                        <span className="bill-summary-total">
                          {formatMoney(bill.balance_due_minor, bill.currency_code)}
                        </span>
                      </div>
                      {chosenMethod.account_hint ? <p className="hint">{chosenMethod.account_hint}</p> : null}
                      {chosenMethod.instructions ? <p className="hint">{chosenMethod.instructions}</p> : null}
                    </div>
                  ) : null}

                  {chosenMethod ? (
                    <div className="verify-block">
                      <label className="verify-label">
                        <input
                          type="checkbox"
                          checked={verified}
                          disabled={busy}
                          onChange={(event) => setVerified(event.target.checked)}
                        />
                        {chosenMethod.kind === "QR"
                          ? `I have checked the ${chosenMethod.label} account and received ${formatMoney(
                              bill.balance_due_minor,
                              bill.currency_code
                            )}.`
                          : `I have counted ${formatMoney(
                              bill.balance_due_minor,
                              bill.currency_code
                            )} in cash from this table.`}
                      </label>
                      {verified ? (
                        <p className="qr-warning" style={{ margin: 0 }}>
                          Verification pending — the bill is still unpaid until you confirm below.
                        </p>
                      ) : null}
                      <button
                        className="btn ok btn-lg"
                        disabled={busy || !verified || bill.balance_due_minor <= 0}
                        onClick={() => void verifyAndRecord()}
                        type="button"
                      >
                        {busy ? "Recording…" : "Verify & mark paid"}
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {bill.status === "ISSUED" && bill.paid_minor === 0 && selected.active_session_id ? (
                <button
                  className="btn ghost"
                  style={{ marginTop: "var(--space-4)" }}
                  disabled={busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Recalculate this bill from the currently accepted items? Line items are rebuilt from the kitchen-accepted orders and any hand edits are lost."
                      )
                    ) {
                      void issue();
                    }
                  }}
                  type="button"
                >
                  Recalculate from accepted items
                </button>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </>
  );
}
