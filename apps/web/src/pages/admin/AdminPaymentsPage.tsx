import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminPaymentsPage() {
  const { admin, has } = usePlatformAuth();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [statusFilter, setStatusFilter] = React.useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPayments() {
      let url = `/api/platform/payments?page=${page}&page_size=${pageSize}`;
      if (statusFilter) url += "&status=" + statusFilter;
      const data = await platformFetch(url);
      setItems(data.items || []);
      setTotal(data.total || 0);
      setLoading(false);
    }

    if (admin && has("invoice.view")) {
      loadPayments();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize, statusFilter]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Payments</h1>
        <p>Loading payments...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Payments</h1>

      {admin && has("invoice.view") ? (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All statuses</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="VOIDED">VOIDED</option>
              <option value="REFUND_PENDING">REFUND_PENDING</option>
              <option value="REFUND_APPROVED">REFUND_APPROVED</option>
              <option value="REFUNDED">REFUNDED</option>
            </select>
          </div>

          {items.length === 0 ? (
            <p>No payments found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Reference</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Invoice</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Tenant</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Amount</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Method</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((pay: any) => (
                  <tr key={pay.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: "8px"}}>{pay.reference}</td>
                    <td style={{ padding: "8px"}}>{pay.invoice_number || "—"}</td>
                    <td style={{ padding: "8px"}}>{pay.tenant_name || "—"}</td>
                    <td style={{ padding: "8px"}}>{Math.floor(pay.amount_minor / 100)} NPR</td>
                    <td style={{ padding: "8px"}}>{pay.method}</td>
                    <td style={{ padding: "8px"}}>{pay.status}</td>
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

