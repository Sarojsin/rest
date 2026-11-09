import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError, formatMoney } from "../../../lib/api";

type PaymentMethodBucket = {
  method: string;
  payment_count: number;
  amount_minor: number;
};

type PaymentsReport = {
  currency_code: string;
  total_collected_minor: number;
  succeeded_count: number;
  failed_count: number;
  methods: PaymentMethodBucket[];
};

export default function ReportsPaymentsPage() {
  const [report, setReport] = useState<PaymentsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const data = await apiFetch<PaymentsReport>("/api/v1/reports/payments");
      setReport(data);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 401)) {
        setForbidden(true);
      } else {
        setError(err instanceof ApiError ? err.detail : "Could not load payments report.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="empty-state">
        <strong>Payments report is restricted</strong>
        <span>
          Your role cannot read restaurant takings. Ask an owner or manager for the payments
          breakdown.
        </span>
      </div>
    );
  }

  const currency = report?.currency_code ?? "USD";
  const methodCount = report?.methods.length ?? 0;

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading payments breakdown…</p> : null}

      {report ? (
        <>
          <section className="report-grid" aria-label="Payments summary">
            <article className="report-card">
              <p className="muted">Collected</p>
              <p className="stat">{formatMoney(report.total_collected_minor, currency)}</p>
              <p className="kpi-foot">{report.succeeded_count} successful payments</p>
            </article>
            <article className="report-card">
              <p className="muted">Failed payments</p>
              <p className="stat">{report.failed_count}</p>
              <p className="kpi-foot">Declined / timed out in window</p>
            </article>
            <article className="report-card">
              <p className="muted">Methods used</p>
              <p className="stat">{methodCount}</p>
              <p className="kpi-foot">Cash vs QR (label-level grouping)</p>
            </article>
          </section>

          <section className="section-card">
            <div className="section-card-head">
              <h3>Breakdown by payment method</h3>
              <span className="muted text-sm">{report.methods.length} method(s)</span>
            </div>
            <div className="section-card-body">
              {report.methods.length === 0 ? (
                <p className="muted">No payments recorded in this window.</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Method</th>
                        <th className="num">Payments</th>
                        <th className="num">Collected</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.methods.map((method) => (
                        <tr key={method.method}>
                          <td>{method.method}</td>
                          <td className="num">{method.payment_count}</td>
                          <td className="num">{formatMoney(method.amount_minor, currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
