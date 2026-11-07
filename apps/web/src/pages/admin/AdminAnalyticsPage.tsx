import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

type Summary = {
  generated_at: string;
  total_restaurants: number;
  new_restaurants_30d: number;
  total_branches: number;
  total_staff: number;
  restaurants_by_status: Record<string, number>;
  subscriptions_by_status: Record<string, number>;
  tickets_by_status: Record<string, number>;
};

export default function AdminAnalyticsPage() {
  const { admin, has } = usePlatformAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAnalytics() {
      setLoading(true);
      setError(null);
      try {
        const data = await platformFetch("/api/platform/analytics/summary");
        setSummary(data);
      } catch (err: any) {
        setError(err.detail || "Failed to load analytics.");
      } finally {
        setLoading(false);
      }
    }

    if (admin && has("analytics.view")) {
      loadAnalytics();
    } else {
      setLoading(false);
    }
  }, [admin, has]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Analytics</h1>
        <p>Loading analytics…</p>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Analytics</h1>
        <p className="pf-muted">No data available.</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Analytics</h1>
      <p className="pf-muted" style={{ marginBottom: 24 }}>
        Platform-wide revenue, growth, and usage metrics.
      </p>

      {error ? <div className="pf-error">{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 6 }}>
            Total Restaurants
          </div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{summary.total_restaurants}</div>
        </div>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 6 }}>
            New (30 days)
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#059669" }}>
            +{summary.new_restaurants_30d}
          </div>
        </div>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 6 }}>
            Total Branches
          </div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{summary.total_branches}</div>
        </div>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 6 }}>
            Total Staff
          </div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{summary.total_staff}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 10 }}>
            Restaurants by Status
          </div>
          <table style={{ width: "100%", fontSize: 13 }}>
            <tbody>
              {Object.entries(summary.restaurants_by_status).map(([status, count]) => (
                <tr key={status} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "6px 0", color: "#334155" }}>{status}</td>
                  <td style={{ padding: "6px 0", textAlign: "right", fontWeight: 600 }}>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 10 }}>
            Subscriptions by Status
          </div>
          <table style={{ width: "100%", fontSize: 13 }}>
            <tbody>
              {Object.entries(summary.subscriptions_by_status).map(([status, count]) => (
                <tr key={status} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "6px 0", color: "#334155" }}>{status}</td>
                  <td style={{ padding: "6px 0", textAlign: "right", fontWeight: 600 }}>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pf-card" style={{ padding: 16, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", marginBottom: 10 }}>
            Support Tickets by Status
          </div>
          <table style={{ width: "100%", fontSize: 13 }}>
            <tbody>
              {Object.entries(summary.tickets_by_status).map(([status, count]) => (
                <tr key={status} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "6px 0", color: "#334155" }}>{status}</td>
                  <td style={{ padding: "6px 0", textAlign: "right", fontWeight: 600 }}>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ marginTop: 24, fontSize: 11, color: "#64748b" }}>
        Generated: {new Date(summary.generated_at).toLocaleString()}
      </div>
    </div>
  );
}


