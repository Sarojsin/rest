import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminUsagePage() {
  const { admin, has } = usePlatformAuth();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUsage() {
      setLoading(true);
      setError(null);
      try {
        // Fetch all tenants first
        const tenantsRes: Response = await platformFetch(
          "/api/platform/tenants?page=1&page_size=100"
        );
        const tenantsData = await tenantsRes.json();
        const tenants = tenantsData.items || [];

        // Fetch usage for each tenant
        const usagePromises = tenants.map(async (t: any) => {
          try {
            const usageRes: Response = await platformFetch(
              `/api/platform/tenants/${t.id}/usage`
            );
            return await usageRes.json();
          } catch {
            return null;
          }
        });
        const usageResults = await Promise.all(usagePromises);

        const combined = tenants.map((t: any, idx: number) => {
          const usage = usageResults[idx];
          const usageByKey: Record<string, any> = {};
          (usage?.usage || {}).forEach((u: any) => {
            usageByKey[u.key] = u;
          });
          return {
            ...t,
            usage: usageByKey,
          };
        });

        setItems(combined);
      } catch (err: any) {
        setError(err.detail || "Failed to load usage data.");
      } finally {
        setLoading(false);
      }
    }

    if (admin && has("tenant.view")) {
      loadUsage();
    } else {
      setLoading(false);
    }
  }, [admin, has]);

  const LIMIT_LABELS: Record<string, string> = {
    branches: "Branches",
    owners: "Owners",
    managers: "Managers",
    waiters: "Waiters",
    kitchen: "Kitchen",
    cashier: "Cashiers",
    tables: "Tables",
  };

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1100 }}>
        <h1 style={{ marginTop: 0 }}>Usage &amp; Limits</h1>
        <p>Loading usage data…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1100 }}>
      <h1 style={{ marginTop: 0 }}>Usage &amp; Limits</h1>
      <p className="pf-muted" style={{ marginBottom: 16 }}>
        Monitor resource usage against plan limits for each tenant.
      </p>

      {error ? <div className="pf-error">{error}</div> : null}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8px" }}>Restaurant</th>
            <th style={{ padding: "12px 8px" }}>Plan</th>
            <th style={{ padding: "12px 8px" }}>Status</th>
            {["branches", "owners", "managers", "waiters", "kitchen", "cashier", "tables"].map(
              (key) => (
                <th
                  key={key}
                  style={{ padding: "12px 8px", fontSize: 11, textTransform: "uppercase" }}
                >
                  {LIMIT_LABELS[key]}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {items.map((item: any) => {
            const u = item.usage || {};
            return (
              <tr key={item.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8px", fontWeight: 500 }}>
                  {item.name}
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>
                  {item.plan_code || "—"}
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>
                  {item.status || "—"}
                </td>
                {["branches", "owners", "managers", "waiters", "kitchen", "cashier", "tables"].map(
                  (key) => {
                    const usage = u[key];
                    const current = usage?.current ?? 0;
                    const limit = usage?.limit;
                    const remaining = usage?.remaining;
                    const atLimit = usage?.atLimit;
                    return (
                      <td
                        key={key}
                        style={{
                          padding: "10px 8px",
                          fontSize: 12,
                          color: atLimit ? "#dc2626" : "#334155",
                          fontWeight: atLimit ? 600 : 400,
                        }}
                      >
                        {current}{limit !== undefined ? ` / ${limit}` : ""}
                        {remaining !== undefined && remaining === 0 && limit !== undefined && limit > 0 ? (
                          <span style={{ marginLeft: 4, fontSize: 10, color: "#dc2626" }}>
                            (at limit)
                          </span>
                        ) : null}
                      </td>
                    );
                  }
                )}
              </tr>
            );
          })}
          {items.length === 0 && (
            <tr>
              <td colSpan={10} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No tenants found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}


