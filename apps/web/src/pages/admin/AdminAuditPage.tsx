import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminAuditPage() {
  const { admin, has } = usePlatformAuth();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [actionFilter, setActionFilter] = React.useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAuditLogs() {
      let url = `/api/platform/audit-logs?page=${page}&page_size=${pageSize}`;
      if (actionFilter) url += "&action=" + actionFilter;
      const res: Response = await platformFetch(url);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setLoading(false);
    }

    if (admin && has("audit.view")) {
      loadAuditLogs();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize, actionFilter]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Audit Log</h1>
        <p>Loading audit entries...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Audit Log</h1>

      {admin && has("audit.view") ? (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              onChange={(e) => setActionFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All actions</option>
              <option value="TENANT_CREATED">TENANT_CREATED</option>
              <option value="TENANT_UPDATED">TENANT_UPDATED</option>
              <option value="TENANT_SUSPENDED">TENANT_SUSPENDED</option>
              <option value="TENANT_REACTIVATED">TENANT_REACTIVATED</option>
              <option value="PAYMENT_RECORDED">PAYMENT_RECORDED</option>
              <option value="INVOICE_CREATED">INVOICE_CREATED</option>
              <option value="INVOICE_VOIDED">INVOICE_VOIDED</option>
            </select>
          </div>

          {items.length === 0 ? (
            <p>No audit entries found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Action</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Actor</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Entity</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Restaurant</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((entry: any) => (
                  <tr key={entry.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: 8 }}>{entry.action}</td>
                    <td style={{ padding: 8 }}>{entry.actor_email || "—"}</td>
                    <td style={{ padding: 8 }}>{entry.entity_type}</td>
                    <td style={{ padding: 8 }}>{entry.tenant_id || "—"}</td>
                    <td style={{ padding: 8 }}>{new Date(entry.created_at).toISOString().slice(0, 10)}</td>
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