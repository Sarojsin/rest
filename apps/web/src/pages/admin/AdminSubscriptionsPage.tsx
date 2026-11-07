import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminSubscriptionsPage() {
  const { admin, has } = usePlatformAuth();
  const navigate = useNavigate();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [statusFilter, setStatusFilter] = React.useState<string | null>(null);
  const [planFilter, setPlanFilter] = React.useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSubscriptions() {
      let url = `/api/platform/subscriptions?page=${page}&page_size=${pageSize}`;
      if (statusFilter) url += "&status=" + statusFilter;
      if (planFilter) url += "&plan=" + planFilter;
      const data = await platformFetch(url);
      
      setItems(data.items || []);
      setTotal(data.total || 0);
      setLoading(false);
    }

    if (admin && has("subscription.view")) {
      loadSubscriptions();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize, statusFilter, planFilter]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Subscriptions</h1>
        <p>Loading subscriptions...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Subscriptions</h1>

      {admin && has("subscription.view") ? (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="TRIALING">TRIALING</option>
              <option value="PAST_DUE">PAST_DUE</option>
            </select>
            <select
              onChange={(e) => setPlanFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All plans</option>
            </select>
          </div>

          {items.length === 0 ? (
            <p>No subscriptions found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Tenant</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Plan</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Trial ends</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((sub: any) => (
                  <tr key={sub.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: "8px"}}>{sub.tenant_name || "—"}</td>
                    <td style={{ padding: "8px"}}>{sub.plan_name || "—"}</td>
                    <td style={{ padding: "8px"}}>{sub.status}</td>
                    <td style={{ padding: "8px"}}>{sub.trial_ends_at ? new Date(sub.trial_ends_at).toISOString().slice(0, 10) : "—"}</td>
                    <td style={{ padding: "8px"}}><button onClick={() => navigate(`/admin/subscriptions/${sub.id}`)}>View</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
            <span>Page {page} of {Math.ceil(total / pageSize)}</span>
          </div>
        </>
      ) : (
        <p className="pf-muted" style={{ color: "red" }}>
          Access denied. <a href="/admin/login">Log in</a> as a platform admin.
        </p>
      )}
    </div>
  );
}


