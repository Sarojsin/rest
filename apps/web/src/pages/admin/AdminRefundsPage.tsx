import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminRefundsPage() {
  const { admin, has } = usePlatformAuth();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRefunds() {
      const url = `/api/platform/refunds?page=${page}&page_size=${pageSize}`;
      const res: Response = await platformFetch(url);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setLoading(false);
    }

    if (admin && has("payment.refund.approve")) {
      loadRefunds();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Refunds</h1>
        <p>Loading refunds...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Refunds</h1>

      {admin && has("payment.refund.approve") ? (
        <>
          {items.length === 0 ? (
            <p>No refunds found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Original Ref</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Tenant</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Amount</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Approved</th>
                </tr>
              </thead>
              <tbody>
                {items.map((ref: any) => (
                  <tr key={ref.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: 8 }}>{ref.reference}</td>
                    <td style={{ padding: 8 }}>{ref.tenant_name || "—"}</td>
                    <td style={{ padding: 8 }}>{Math.floor(ref.amount_minor / 100)} NPR</td>
                    <td style={{ padding: 8 }}>{ref.status}</td>
                    <td style={{ padding: 8 }}>{ref.refund_approved_by_admin_id ? "Yes" : "Pending"}</td>
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