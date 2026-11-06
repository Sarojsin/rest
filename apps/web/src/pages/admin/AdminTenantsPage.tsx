import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminTenantsPage() {
  const { admin, has } = usePlatformAuth();
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = React.useState<string | null>(null);
  const [planFilter, setPlanFilter] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState<string>("");
  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTenants() {
      let url = "/api/platform/tenants?page=" + page + "&page_size=" + pageSize;
      if (statusFilter) url += "&status=" + statusFilter;
      if (planFilter) url += "&plan=" + planFilter;
      if (search) url += "&q=" + encodeURIComponent(search);
      const res: Response = await platformFetch(url);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setLoading(false);
    }

    if (admin && has("tenant.view")) {
      loadTenants();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize, statusFilter, planFilter, search]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Tenants</h1>
        <p>Loading tenants...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Tenants</h1>

      {admin && has("tenant.view") ? (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="SUSPENDED">SUSPENDED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
            <select
              onChange={(e) => setPlanFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All plans</option>
              {[...new Set(items.map((t: any) => t.plan_code) as string[]), ""]
                .filter(Boolean)
                .map((code) => (
                  <option key={code} value={code}>
                    {code.toUpperCase()}
                  </option>
                ))}
            </select>
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ marginRight: 8, width: 200 }}
            />
            <button
              onClick={() => navigate("/admin/tenants/create")}
              style={{
                marginLeft: 8,
                background: "#3a6df0",
                color: "white",
                border: "none",
                padding: "6px 12px",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Create
            </button>
          </div>

          {items.length === 0 ? (
            <p>No tenants found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Name</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Slug</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Plan</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Staff</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t: any) => (
                  <tr key={t.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: "8px"}}>{t.name}</td>
                    <td style={{ padding: "8px"}}>{t.slug}</td>
                    <td style={{ padding: "8px"}}>{t.plan_code}</td>
                    <td style={{ padding: "8px"}}>{t.subscription_status}</td>
                    <td style={{ padding: "8px"}}>{t.staff}</td>
                    <td style={{ padding: "8px"}}>{t.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
            <span>
              Page {page} of {Math.ceil(total / pageSize)}
            </span>
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