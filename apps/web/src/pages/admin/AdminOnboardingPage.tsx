import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminOnboardingPage() {
  const { admin, has } = usePlatformAuth();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadOnboarding() {
      setLoading(true);
      setError(null);
      try {
        const res: Response = await platformFetch(
          `/api/platform/onboarding?page=${page}&page_size=${pageSize}`
        );
        
        setItems(data.items || []);
        setTotal(data.total || 0);
      } catch (err: any) {
        setError(err.detail || "Failed to load onboarding statuses.");
      } finally {
        setLoading(false);
      }
    }

    if (admin && has("tenant.view")) {
      loadOnboarding();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize]);

  const STAGE_LABELS: Record<string, string> = {
    registered: "Registered",
    owner_invited: "Owner Invited",
    owner_activated: "Owner Activated",
    profile_complete: "Profile Complete",
    tables_configured: "Tables Configured",
    menu_configured: "Menu Configured",
    staff_invited: "Staff Invited",
    payments_configured: "Payments Configured",
    operational: "Operational",
  };

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1100 }}>
        <h1 style={{ marginTop: 0 }}>Onboarding</h1>
        <p>Loading onboarding statuses…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1100 }}>
      <h1 style={{ marginTop: 0 }}>Onboarding</h1>
      <p className="pf-muted" style={{ marginBottom: 16 }}>
        Track restaurant onboarding from registration to first order.
      </p>

      {error ? <div className="pf-error">{error}</div> : null}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8px" }}>Restaurant</th>
            <th style={{ padding: "12px 8px" }}>Slug / Tenant ID</th>
            <th style={{ padding: "12px 8px" }}>Stage</th>
            <th style={{ padding: "12px 8px" }}>Subscription</th>
            <th style={{ padding: "12px 8px" }}>Trial Ends</th>
            <th style={{ padding: "12px 8px" }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item: any) => (
            <tr key={item.tenant_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
              <td style={{ padding: "10px 8px", fontWeight: 500 }}>
                {item.name}
              </td>
              <td style={{ padding: "10px 8px", fontSize: 12, color: "#64748b" }}>
                {item.slug}<br />
                <span style={{ fontSize: 11 }}>{item.tenant_id}</span>
              </td>
              <td style={{ padding: "10px 8px" }}>
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 10,
                    fontSize: 11,
                    background: "#f1f5f9",
                    color: "#475569",
                  }}
                >
                  {STAGE_LABELS[item.onboarding_stage] || item.onboarding_stage}
                </span>
              </td>
              <td style={{ padding: "10px 8px" }}>
                {item.subscription_status || "—"}
              </td>
              <td style={{ padding: "10px 8px", fontSize: 12 }}>
                {item.trial_ends_at ? new Date(item.trial_ends_at).toLocaleDateString() : "—"}
              </td>
              <td style={{ padding: "10px 8px", fontSize: 12 }}>
                {new Date(item.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No tenants found.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {total > pageSize && (
        <div style={{ marginTop: 16, display: "flex", justifyContent: "center", gap: 8 }}>
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="pf-button secondary"
          >
            Prev
          </button>
          <span style={{ fontSize: 12, color: "#64748b" }}>
            Page {page} of {Math.ceil(total / pageSize)}
          </span>
          <button
            disabled={page * pageSize >= total}
            onClick={() => setPage(page + 1)}
            className="pf-button secondary"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}



