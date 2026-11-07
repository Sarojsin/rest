import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

type TenantEntitlement = {
  restaurant_id: string;
  subscription_id: string | null;
  plan_version_id: string | null;
  usage: Record<string, { current: number; limit: number | null; remaining: number | null; at_limit: boolean }>;
};

export default function AdminTenantEntitlementsPage() {
  const { admin, has } = usePlatformAuth();
  const [tenants, setTenants] = useState<TenantEntitlement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reconciling, setReconciling] = useState<string | null>(null);

  useEffect(() => {
    loadEntitlements();
  }, []);

  async function loadEntitlements() {
    try {
      setLoading(true);
      const tenantsRes = await platformFetch("/api/platform/tenants");
      if (!tenantsRes.ok) throw new Error("Failed to load tenants");
      const tenantsData = await tenantsRes.json();
      const tenantList = tenantsData.items || [];

      const entitlements: TenantEntitlement[] = [];
      for (const t of tenantList) {
        try {
          const entRes = await platformFetch(`/api/platform/tenants/${t.id}/entitlements`);
          if (entRes.ok) {
            const entData = await entRes.json();
            entitlements.push({
              restaurant_id: t.id,
              subscription_id: entData.subscription_id,
              plan_version_id: entData.plan_version_id,
              usage: entData.usage || {},
            });
          }
        } catch {
          // Skip tenants with errors
        }
      }
      setTenants(entitlements);
    } catch (err: any) {
      setError(err.message || "Failed to load entitlements");
    } finally {
      setLoading(false);
    }
  }

  async function reconcile(restaurantId: string) {
    setReconciling(restaurantId);
    try {
      const res = await platformFetch(`/api/platform/tenants/${restaurantId}/reconcile`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Reconciliation failed");
      await loadEntitlements();
    } catch (err: any) {
      setError(err.message || "Reconciliation failed");
    } finally {
      setReconciling(null);
    }
  }

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1400 }}>
        <h1 style={{ marginTop: 0 }}>Tenant Entitlements</h1>
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Tenant Entitlements</h1>
        <p className="pf-error">{error}</p>
        <button onClick={() => window.location.href = "/admin/tenants"}>Back to Tenants</button>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1400 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ margin: "0"}}>Tenant Entitlements & Usage</h1>
        <button
          onClick={loadEntitlements}
          className="pf-button secondary"
          disabled={loading}
        >
          Refresh
        </button>
      </div>

      {error && <div className="pf-error" style={{ marginBottom: 16 }}>{error}</div>}

      <p className="pf-muted" style={{ marginBottom: 16 }}>
        View current usage vs plan limits for each tenant. Tenants at or over their limit
        cannot create new staff, branches, or other resources until they upgrade or an admin
        increases their plan limits.
      </p>

      {tenants.length === 0 ? (
        <p>No tenants with active subscriptions found.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #d9dde5" }}>
              <th style={{ padding: 10, textAlign: "left" }}>Tenant</th>
              <th style={{ padding: 10, textAlign: "left" }}>Plan Version</th>
              <th style={{ padding: 10, textAlign: "left" }}>Staff</th>
              <th style={{ padding: 10, textAlign: "left" }}>Branches</th>
              <th style={{ padding: 10, textAlign: "left" }}>Waiters</th>
              <th style={{ padding: 10, textAlign: "left" }}>Tables</th>
              <th style={{ padding: 10, textAlign: "left" }}>Status</th>
              <th style={{ padding: 10, textAlign: "left" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => {
              const u = t.usage;
              const branches = u.branches || { current: 0, limit: null, remaining: null, at_limit: false };
              const waiters = u.waiters || { current: 0, limit: null, remaining: null, at_limit: false };
              const tables = u.tables || { current: 0, limit: null, remaining: null, at_limit: false };
              const staff = u.staff || { current: 0, limit: null, remaining: null, at_limit: false };
              const anyAtLimit = [branches, waiters, tables, staff].some((u) => u.at_limit);
              const anyNearLimit = [branches, waiters, tables, staff].some(
                (u) => u.remaining !== null && u.remaining <= 2 && u.remaining > 0
              );

              return (
                <tr key={t.restaurant_id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                  <td style={{ padding: "10px"}}>{t.restaurant_id}</td>
                  <td style={{ padding: "10px"}}>
                    {t.plan_version_id ? (
                      <span
                        style={{
                          padding: "4px 8px",
                          borderRadius: 4,
                          background: "#e7f4ea",
                          color: "#17643b",
                          fontSize: 11,
                        }}
                      >
                        v{t.plan_version_id.slice(-4)}
                      </span>
                    ) : (
                      <span style={{ color: "#5b6678" }}>No version</span>
                    )}
                  </td>
                  <td style={{ padding: "10px"}}>
                    {staff.current} / {staff.limit ?? "∞"}
                  </td>
                  <td style={{ padding: "10px"}}>
                    {branches.current} / {branches.limit ?? "∞"}
                  </td>
                  <td style={{ padding: "10px"}}>
                    {waiters.current} / {waiters.limit ?? "∞"}
                  </td>
                  <td style={{ padding: "10px"}}>
                    {tables.current} / {tables.limit ?? "∞"}
                  </td>
                  <td style={{ padding: "10px"}}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: 4,
                        background: anyAtLimit ? "#fdecea" : anyNearLimit ? "#fff4e5" : "#e7f4ea",
                        color: anyAtLimit ? "#b3261e" : anyNearLimit ? "#9a6200" : "#17643b",
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      {anyAtLimit ? "AT LIMIT" : anyNearLimit ? "NEAR LIMIT" : "OK"}
                    </span>
                  </td>
                  <td style={{ padding: "10px"}}>
                    {admin && has("platform.manage") && (
                      <button
                        onClick={() => reconcile(t.restaurant_id)}
                        disabled={reconciling === t.restaurant_id}
                        className="pf-button secondary"
                        style={{ padding: "4px 8px", fontSize: 11 }}
                      >
                        {reconciling === t.restaurant_id ? "Reconciling..." : "Reconcile"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      <div style={{ marginTop: 24, borderTop: "1px solid #d9dde5", paddingTop: 16 }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: 14 }}>Understanding Entitlements</h3>
        <ul style={{ margin: 0, paddingLeft: 20, color: "#5b6678", fontSize: 13 }}>
          <li>Current = number of resources currently used by the tenant</li>
          <li>Limit = maximum allowed by the tenant's active plan version</li>
          <li>Remaining = how many more can be created before hitting the limit</li>
          <li>At Limit = tenant cannot create more of this resource without upgrading</li>
          <li>Reconcile = recalculate cached counters from the audit ledger</li>
        </ul>
      </div>
    </div>
  );
}

