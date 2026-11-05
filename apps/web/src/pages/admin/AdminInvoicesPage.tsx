import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminInvoicesPage() {
  const { admin, has } = usePlatformAuth();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [statusFilter, setStatusFilter] = React.useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadInvoices() {
      let url = `/api/platform/invoices?page=${page}&page_size=${pageSize}`;
      if (statusFilter) url += "&status=" + statusFilter;
      const res: Response = await platformFetch(url);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setLoading(false);
    }

    if (admin && has("invoice.view")) {
      loadInvoices();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize, statusFilter]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Invoices</h1>
        <p>Loading invoices...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Invoices</h1>

      {admin && has("invoice.view") ? (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="PAID">PAID</option>
              <option value="OVERDUE">OVERDUE</option>
              <option value="VOID">VOID</option>
              <option value="REFUNDED">REFUNDED</option>
            </select>
          </div>

          {items.length === 0 ? (
            <p>No invoices found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Invoice #</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Tenant</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Plan</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Amount</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Due</th>
                </tr>
              </thead>
              <tbody>
                {items.map((inv: any) => (
                  <tr key={inv.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: 8 }}>{inv.invoice_number}</td>
                    <td style={{ padding: 8 }}>{inv.tenant_name || "—"}</td>
                    <td style={{ padding: 8 }}>{inv.plan_code || "—"}</td>
                    <td style={{ padding: 8 }}>{inv.status}</td>
                    <td style={{ padding: 8 }}>{Math.floor(inv.total_minor / 100)} NPR</td>
                    <td style={{ padding: 8 }}>{new Date(inv.due_at).toISOString().slice(0, 10)}</td>
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