import { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminPlatformUsersPage() {
  const { admin, has } = usePlatformAuth();

  const [page] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [roleFilter, setRoleFilter] = React.useState<string | null>(null);
  const [statusFilter, setStatusFilter] = React.useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [activeSuperadmins, setActiveSuperadmins] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPlatformUsers() {
      let url = `/api/platform/platform-users?page=${page}&page_size=${pageSize}`;
      if (roleFilter) url += "&role=" + roleFilter;
      if (statusFilter) url += "&status=" + statusFilter;
      const res: Response = await platformFetch(url);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setActiveSuperadmins(data.active_superadmins || 0);
      setLoading(false);
    }

    if (admin && has("platform_user.view")) {
      loadPlatformUsers();
    } else {
      setLoading(false);
    }
  }, [admin, has, page, pageSize, roleFilter, statusFilter]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Platform Users</h1>
        <p>Loading platform users...</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Platform Users</h1>

      {admin && has("platform_user.view") ? (
        <>
          <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
            <select
              onChange={(e) => setRoleFilter(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="">All roles</option>
              <option value="superadmin">superadmin</option>
              <option value="billing">billing</option>
              <option value="ops">ops</option>
              <option value="support">support</option>
            </select>
            <select
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginLeft: 8, flex: 1 }}
            >
              <option value="">All statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="INVITED">INVITED</option>
              <option value="DISABLED">DISABLED</option>
            </select>
          </div>

          {items.length === 0 ? (
            <p>No platform users found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Email</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Role</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 8, textAlign: "left" }}>MFA</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Recovery</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Last auth</th>
                </tr>
              </thead>
              <tbody>
                {items.map((user: any) => (
                  <tr key={user.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                    <td style={{ padding: "8px"}}>{user.email}</td>
                    <td style={{ padding: "8px"}}>{user.role}</td>
                    <td style={{ padding: "8px"}}>{user.status}</td>
                    <td style={{ padding: "8px"}}>{user.mfa_enabled ? "Yes" : "No"}</td>
                    <td style={{ padding: "8px"}}>{user.recovery_codes_remaining || 0}</td>
                    <td style={{ padding: "8px"}}>{user.last_auth_at ? new Date(user.last_auth_at).toISOString().slice(0, 10) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
            <span>
              Page {page} of {Math.ceil(total / pageSize)} &nbsp;|&nbsp;
              Active superadmins: {activeSuperadmins || 0}
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