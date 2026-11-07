import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminOnboardingPage() {
  const { admin, has, loading: authLoading, error: authError } = usePlatformAuth();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"pending" | "all" | "approved">("pending");

  // Available status filters with labels
  const STATUS_FILTERS = [
    { key: "pending", label: "Pending", count: 0 },
    { key: "approved", label: "Approved", count: 0 },
    { key: "rejected", label: "Rejected", count: 0 },
  ];

  const STAGE_LABELS: Record<string, string> = {
    "REGISTERED": "Registered",
    "APPROVED": "Approved",
    "INVITED": "Invited",
    "MFA_SETUP": "MFA Setup",
    "ONBOARDING_COMPLETE": "Complete",
    "REJECTED": "Rejected",
    "PENDING": "Pending",
  };

  useEffect(() => {
    async function loadOnboarding() {
      setLoading(true);
      setError(null);
      try {
        // Always load onboarding data - permission check happens inside the API
        // Build query parameters based on status filter
        const statusParam = statusFilter === "pending" ? "PENDING" : 
                           statusFilter === "approved" ? "APPROVED" : "";
        
        let url = `/api/platform/onboarding?page=${page}&page_size=${pageSize}`;
        if (statusParam) {
          url += `&status=${statusParam}`;
        }
        
        const res: Response = await platformFetch(url);
        const data = await res.json();
        
        setItems(data.items || []);
        setTotal(data.total || 0);
      } catch (err: any) {
        setError(err.detail || "Failed to load onboarding statuses.");
        // Fallback: try without status filter
        try {
          const res: Response = await platformFetch(
            `/api/platform/onboarding?page=${page}&page_size=${pageSize}`
          );
          const data = await res.json();
          setItems(data.items || []);
          setTotal(data.total || 0);
        } catch (err2: any) {
          setError(err2.detail || "Failed to load onboarding statuses.");
        }
      } finally {
        setLoading(false);
      }
    }

    // Load data if admin is available, or if auth is done loading
    if (admin) {
      loadOnboarding();
    } else if (authLoading === false) {
      // Try loading data even without full admin context
      loadOnboarding();
    }
  }, [admin, page, pageSize, statusFilter]);

  // Compute filtered item counts per status
  const statusCounts = {
    pending: items.filter((item: any) => item.status === "PENDING").length,
    approved: items.filter((item: any) => item.status === "APPROVED").length,
    rejected: items.filter((item: any) => item.status === "REJECTED").length,
  };

  // Apply status filter
  const filteredItems = statusFilter === "pending"
    ? items.filter((item: any) => item.status === "PENDING")
    : statusFilter === "approved"
      ? items.filter((item: any) => item.status === "APPROVED")
      : items;

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

      {/* Status Filter Controls */}
      <div style={{ marginBottom: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.key}
            onClick={() => setStatusFilter(filter.key)}
            style={{
              background: statusFilter === filter.key 
                ? "var(--pf-color-primary)" 
                : "transparent",
              color: statusFilter === filter.key 
                ? "white" 
                : "var(--pf-color-primary)",
              border: statusFilter === filter.key 
                ? "none" 
                : "1px solid var(--pf-color-primary)",
              borderRadius: 4,
              padding: "6px 12px",
              fontSize: 12,
              minWidth: 100,
            }}
          >
            {filter.label} ({statusCounts[filter.key]})
          </button>
        ))}
      </div>

      {error ? <div className="pf-error">{error}</div> : null}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8" }}>Restaurant</th>
            <th style={{ padding: "12px 8" }}>Slug / Tenant ID</th>
            <th style={{ padding: "12px 8" }}>Stage</th>
            <th style={{ padding: "12px 8" }}>Subscription</th>
            <th style={{ padding: "12px 8" }}>Trial Ends</th>
            <th style={{ padding: "12px 8" }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {filteredItems.length > 0 ? (
            filteredItems.map((item: any) => (
              <tr key={item.tenant_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8", fontWeight: 500 }}>
                  {item.name}
                </td>
                <td style={{ padding: "10px 8", fontSize: 12, color: "#64748b" }}>
                  {item.slug}<br />
                  <span style={{ fontSize: 11 }}>{item.tenant_id}</span>
                </td>
                <td style={{ padding: "10px 8" }}>
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
                    {STAGE_LABELS[item.onboarding_stage] || item.onboarding_stage || "—"}
                  </span>
                </td>
                <td style={{ padding: "10px 8" }}>
                  {item.subscription_status || "—"}
                </td>
                <td style={{ padding: "10px 8", fontSize: 12 }}>
                  {item.trial_ends_at ? new Date(item.trial_ends_at).toLocaleDateString() : "—"}
                </td>
                <td style={{ padding: "10px 8", fontSize: 12 }}>
                  {new Date(item.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                {statusFilter === "pending"
                  ? "No pending registrations found."
                  : statusFilter === "approved"
                    ? "No approved registrations found."
                    : "No rejected registrations found."}
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