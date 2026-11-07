import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";
import { useNavigate } from "react-router-dom";

export default function AdminTenantsPage() {
  const { admin, has, loading: authLoading, error: authError } = usePlatformAuth();
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"ACTIVE" | "SUSPENDED" | "ARCHIVED">("ACTIVE");

  // Available status filters
  const STATUS_FILTERS = [
    { key: "ACTIVE", label: "Active", count: 0 },
    { key: "SUSPENDED", label: "Suspended", count: 0 },
    { key: "ARCHIVED", label: "Archived", count: 0 },
  ];

  useEffect(() => {
    async function loadTenants() {
      setLoading(true);
      setError(null);
      try {
        const statusParam = statusFilter !== "ACTIVE" ? `&status=${statusFilter}` : "";
        const url = `/api/platform/tenants?page=${page}&page_size=${pageSize}${statusParam}`;
        const res: Response = await platformFetch(url);
        const data: any = await res.json();
        setTenants(data.items || []);
        setTotal(data.total || 0);
      } catch (err: any) {
        setError(err.detail || "Failed to load tenants.");
      } finally {
        setLoading(false);
      }
    }

    // Load if admin is available
    if (admin) {
      loadTenants();
    } else if (authLoading === false) {
      // Try loading even without full admin context
      loadTenants();
    }
  }, [admin, page, pageSize]);

  // Compute status counts
  const statusCounts = {
    ACTIVE: tenants.filter((t: any) => t.status === "ACTIVE").length,
    SUSPENDED: tenants.filter((t: any) => t.status === "SUSPENDED").length,
    ARCHIVED: tenants.filter((t: any) => t.status === "ARCHIVED").length,
  };

  // Apply status filter
  const filteredTenants = statusFilter === "ACTIVE"
    ? tenants.filter((t: any) => t.status === "ACTIVE")
    : statusFilter === "SUSPENDED"
      ? tenants.filter((t: any) => t.status === "SUSPENDED")
      : tenants.filter((t: any) => t.status === "ARCHIVED");

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Tenants</h1>
        <p>Loading tenants…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <h1 style={{ marginTop: 0 }}>Tenants</h1>
      {error ? <div className="pf-error">{error}</div> : null}

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

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8" }}>Name</th>
            <th style={{ padding: "12px 8" }}>Slug</th>
            <th style={{ padding: "12px 8" }}>Plan</th>
            <th style={{ padding: "12px 8" }}>Status</th>
            <th style={{ padding: "12px 8" }}>Staff</th>
            <th style={{ padding: "12px 8" }}>Created</th>
            <th style={{ padding: "12px 8" }}></th>
          </tr>
        </thead>
        <tbody>
          {filteredTenants.length > 0 ? (
            filteredTenants.map((tenant: any) => (
              <tr key={tenant.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8", fontWeight: 500 }}>
                  {tenant.name}
                </td>
                <td style={{ padding: "10px 8", fontSize: 12, color: "#64748b" }}>
                  {tenant.slug}
                </td>
                <td style={{ padding: "10px 8" }}>
                  {tenant.plan_code || "—"}
                </td>
                <td style={{ padding: "10px 8" }}>
                  {tenant.status === "ACTIVE"
                    ? "Active"
                    : tenant.status === "SUSPENDED"
                    ? "Suspended"
                    : "Archived"}
                </td>
                <td style={{ padding: "10px 8", fontSize: 12 }}>
                  {tenant.staff_count || "—"}
                </td>
                <td style={{ padding: "10px 8", fontSize: 12 }}>
                  {new Date(tenant.created_at).toLocaleDateString()}
                </td>
                <td style={{ padding: "10px 8" }}>
                  <button
                    className="pf-button secondary"
                    onClick={() =>
                      navigate(`/tenants/${tenant.id}`)
                    }
                  >
                    View
                  </button>
                  <button
                    className="pf-button"
                    onClick={() =>
                      navigate(`/tenants/${tenant.id}/edit`)
                    }
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                {statusFilter === "ACTIVE"
                  ? "No active tenants found."
                  : statusFilter === "SUSPENDED"
                    ? "No suspended tenants found."
                    : "No archived tenants found."}
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {/* Pagination */}
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

      {/* Create Tenant Button */}
      <div style={{ marginTop: 24 }}>
        <button
          className="pf-button primary"
          onClick={() => navigate("/tenants/create")}
        >
          Create Tenant
        </button>
      </div>
    </div>
  );
}