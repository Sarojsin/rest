import { useCallback, useEffect, useState } from "react";
import { apiFetch, formatMoney, ApiError } from "../../../lib/api";

type AdvancedSales = {
  sales: {
    currency_code: string;
    order_count: number;
    accepted_order_count: number;
    cancelled_order_count: number;
    gross_sales_minor: number;
    tax_minor: number;
    collected_minor: number;
    outstanding_minor: number;
    top_items: Array<{ name: string; quantity: number; sales_minor: number }>;
  };
  average_order_minor: number;
  daily: Array<{
    date: string;
    order_count: number;
    gross_sales_minor: number;
  }>;
};

const RANGES = [7, 30, 90] as const;

export default function ReportsDailyPage() {
  const [days, setDays] = useState<number>(7);
  const [report, setReport] = useState<AdvancedSales | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const data = await apiFetch<AdvancedSales>(`/api/v1/reports/advanced?days=${days}`);
      setReport(data);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 401)) {
        setForbidden(true);
      } else {
        setError(err instanceof ApiError ? err.detail : "Could not load daily trend.");
      }
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    void load();
  }, [load]);

  const totals = report
    ? report.daily.reduce(
        (acc, row) => ({
          orders: acc.orders + row.order_count,
          sales: acc.sales + row.gross_sales_minor,
        }),
        { orders: 0, sales: 0 }
      )
    : null;

  if (forbidden) {
    return (
      <div className="page">
        <div className="empty-state">
          <strong>Daily trend is a plan feature</strong>
          <span>
            The advanced reporting feature is not included in this restaurant's plan. Ask the platform
            owner or upgrade to unlock daily bucketed trends.
          </span>
        </div>
      </div>
    );
  }

  const currency = report?.sales.currency_code ?? "USD";

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading daily trend…</p> : null}

      <div className="segmented" role="group" aria-label="Trend window">
        {RANGES.map((range) => (
          <button
            key={range}
            type="button"
            aria-pressed={days === range}
            onClick={() => setDays(range)}
          >
            {range} days
          </button>
        ))}
      </div>

      {totals ? (
        <section className="report-grid" aria-label="Window totals">
          <article className="report-card">
            <p className="muted">Orders in window</p>
            <p className="stat">{totals.orders}</p>
            <p className="kpi-foot">Submitted within last {days} days</p>
          </article>
          <article className="report-card">
            <p className="muted">Sales in window</p>
            <p className="stat">{formatMoney(totals.sales, currency)}</p>
            <p className="kpi-foot">Accepted + completed orders</p>
          </article>
          <article className="report-card">
            <p className="muted">Average order value</p>
            <p className="stat">
              {formatMoney(report?.average_order_minor ?? 0, currency)}
            </p>
            <p className="kpi-foot">All-time average</p>
          </article>
          <article className="report-card">
            <p className="muted">Active days</p>
            <p className="stat">
              {report?.daily.filter((row) => row.order_count > 0).length ?? 0}
            </p>
            <p className="kpi-foot">Days with at least one order</p>
          </article>
        </section>
      ) : null}

      {report ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Daily breakdown</h3>
            <span className="muted text-sm">{report.daily.length} days</span>
          </div>
          <div className="section-card-body">
            {report.daily.length === 0 ? (
              <p className="muted">No orders recorded in this window.</p>
            ) : (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th className="num">Orders</th>
                      <th className="num">Gross sales</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.daily.map((row) => (
                      <tr key={row.date}>
                        <td>{row.date}</td>
                        <td className="num">{row.order_count}</td>
                        <td className="num">{formatMoney(row.gross_sales_minor, currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
