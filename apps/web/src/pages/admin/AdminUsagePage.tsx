import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";
import { useNavigate } from "react-router-dom";

export default function AdminUsagePage() {
  const { admin, has, loading: authLoading, error: authError } = usePlatformAuth();
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUsageData() {
      setLoading(true);
      setError(null);
      try {
        // Load all tenants first
        const res: Response = await platformFetch(
          `/api/platform/tenants?page=1&page_size=100`
        );
        const data: any = await res.json();
        setTenants(data.items || []);
      } catch (err: any) {
        setError(err.detail || "Failed to load tenants.");
      }
      // Now load usage for each tenant
      const data: any = await res.json;
      const tenantList = data.items || [];
      if (tenantList.length > 0) {
        try {
          const usagePromises = tenantList.map((tenant: any) =>
            platformFetch(`/api/platform/tenants/${tenant.id}/usage`)
              .then((r) => r.json())
              .catch(() => ({ branches: 0, tables: 0, owners: 0, waiters: 0, total_connections: 0, daily_revenue: 0 }))
          );
          const usageResults = await Promise.all(usagePromises);
          setTenants(tenantList.map((tenant: any, i: number) => ({
            ...tenant,
            branches: usageResults[i]?.branches ?? tenant.branches,
            tables: usageResults[i]?.tables ?? tenant.tables,
            owners: usageResults[i]?.owners ?? tenant.owners,
            waiters: usageResults[i]?.waiters ?? tenant.waiters,
          })));
        } catch {
          setTenants(tenantList);
        }
      } else {
        setTenants([]);
      }
    }

    // Load if admin is available
    if (admin) {
      loadUsageData();
    } else if (authLoading === false) {
      // Try loading even without full admin context
      loadUsageData();
    }
  }, [admin]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Usage & Limits</h1>
        <p>Loading usage data…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <h1 style={{ marginTop: 0 }}>Usage & Limits</h1>
      {error ? <div className="pf-error">{error}</div> : null}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8" }}>Restaurant</th>
            <th style={{ padding: "12px 8" }}>Plan</th>
            <th style={{ padding: "12px 8" }}>Status</th>
            <th style={{ padding: "12px 8" }}>Branches</th>
            <th style={{ padding: "12px 8" }}>Owners</th>
            <th style={{ padding: "12px 8" }}>Waiters</th>
            <th style={{ padding: "12px 8" }}>Tables</th>
            <th style={{ padding: "12px 8" }}></th>
          </tr>
        </thead>
        <tbody>
          {tenants.length > 0 ? (
            tenants.map((tenant: any) => (
              <tr key={tenant.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8", fontWeight: 500 }}>
                  {tenant.name}
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
                <td style={{ padding: "10px 8" }}>{tenant.branches || "—"}</td>
                <td style={{ padding: "10px 8" }}>{tenant.owners || "—"}</td>
                <td style={{ padding: "10px 8" }}>{tenant.waiters || "—"}</td>
                <td style={{ padding: "10px 8" }}>{tenant.tables || "—"}</td>
                <td style={{ padding: "10px 8" }}>
                  <button
                    className="pf-button secondary"
                    onClick={() =>
                      navigate(`/tenants/${tenant.id}`)
                    }
                  >
                    View
                  </button>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={9} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No tenants found.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {/* Summary section */}
      <div style={{ marginTop: 32 }}>
        <h3>Summary</h3>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <div>
            <strong>Total Tenants:</strong> {tenants.length}
          </div>
          <div>
            <strong>Active:</strong> {tenants.filter((t: any) => t.status === "ACTIVE").length}
          </div>
          <div>
            <strong>Total Branches:</strong> {tenants.reduce((sum: number, t: any) => sum + (t.branches || 0), 0)}
          </div>
          <div>
            <strong>Total Tables:</strong> {tenants.reduce((sum: number, t: any) => sum + (t.tables || 0), 0)}
          </div>
        </div>
      </div>
    </div>
  );
}