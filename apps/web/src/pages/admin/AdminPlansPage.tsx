import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";
import { useNavigate } from "react-router-dom";

export default function AdminPlansPage() {
  const { admin, has, loading: authLoading, error: authError } = usePlatformAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPlans() {
      setLoading(true);
      setError(null);
      try {
        // Super admins can see all plans; tenant admins see only their plans
        const res: Response = await platformFetch(`/api/platform/plans`);
        const data = await res.json();
        setPlans(data.items || []);
      } catch (err: any) {
        setError(err.detail || "Failed to load plans.");
      } finally {
        setLoading(false);
      }
    }

    // Load if admin is available
    if (admin) {
      loadPlans();
    } else if (authLoading === false) {
      // Try loading even without full auth
      loadPlans();
    }
  }, [admin]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Plans</h1>
        <p>Loading plans…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <h1 style={{ marginTop: 0 }}>Plans</h1>
      {error ? <div className="pf-error">{error}</div> : null}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8" }}>Code</th>
            <th style={{ padding: "12px 8" }}>Name</th>
            <th style={{ padding: "12px 8" }}>Description</th>
            <th style={{ padding: "12px 8" }}>Price (Monthly)</th>
            <th style={{ padding: "12px 8" }}>Trial Days</th>
            <th style={{ padding: "12px 8" }}>Status</th>
            <th style={{ padding: "12px 8" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {plans.length > 0 ? (
            plans.map((plan: any) => (
              <tr key={plan.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8" }}>{plan.code}</td>
                <td style={{ padding: "10px 8" }}>{plan.name}</td>
                <td style={{ padding: "10px 8" }}>{plan.description || "—"}</td>
                <td style={{ padding: "10px 8" }}>
                  {plan.price_annual_minor / 100}
                </td>
                <td style={{ padding: "10px 8" }}>{plan.trial_days || "—"}</td>
                <td style={{ padding: "10px 8" }}>
                  {plan.status === "ACTIVE" ? "Active" : plan.status}
                </td>
                <td style={{ padding: "10px 8" }}>
                  <button
                    className="pf-button secondary"
                    onClick={() =>
                      navigate(`/plans/${plan.id}/versions`)
                    }
                  >
                    Versions
                  </button>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No plans found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}