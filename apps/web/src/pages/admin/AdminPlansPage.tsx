import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminPlansPage() {
  const { admin, has } = usePlatformAuth();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPlans() {
      const url = `/api/platform/plans?page=${page}&page_size=${pageSize}`;
      const data = await platformFetch(url);
      
      setItems(data.items || []);
      setLoading(false);
    }

    if (admin && has("plan.view")) {
      loadPlans();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Plans</h1>
        <p>Loading plans...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Plans</h1>

      {admin && has("plan.view") ? (
        <>
          {items.length === 0 ? (
            <p>No plans found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Code</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Name</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Monthly</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Annual</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Trial</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((plan: any) => (
                  <tr key={plan.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: "8px"}}>{plan.code}</td>
                    <td style={{ padding: "8px"}}>{plan.name}</td>
                    <td style={{ padding: "8px"}}>{Math.floor(plan.price_monthly_minor / 100)}</td>
                    <td style={{ padding: "8px"}}>{Math.floor(plan.price_annual_minor / 100)}</td>
                    <td style={{ padding: "8px"}}>{plan.trial_days} days</td>
                    <td style={{ padding: "8px"}}>{plan.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
            <span>Page {page} of {Math.ceil(items.length / pageSize || 1)}</span>
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


