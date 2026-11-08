import React, { useEffect, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

type PlatformUserInvite = {
  email: string;
  display_name: string;
  role: string;
  reason: string;
};

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
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteDraft, setInviteDraft] = useState<PlatformUserInvite>({
    email: "",
    display_name: "",
    role: "support",
    reason: "",
  });
  const [pendingInvite, setPendingInvite] = useState<{
    email: string;
    token: string;
    accept_url: string;
  } | null>(null);

  const ROLES = ["superadmin", "billing", "ops", "support"];

  useEffect(() => {
    let cancelled = false;
    async function loadPlatformUsers() {
      let url = `/api/platform/platform-users?page=${page}&page_size=${pageSize}`;
      if (roleFilter) url += "&role=" + roleFilter;
      if (statusFilter) url += "&status=" + statusFilter;
      const data = await platformFetch(url);
      if (cancelled) return;
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
    return () => {
      cancelled = true;
    };
  }, [admin, has, page, pageSize, roleFilter, statusFilter]);

  async function handleInvite(event: React.FormEvent) {
    event.preventDefault();
    setInviteError(null);
    setInviteBusy(true);
    try {
      const data = await platformFetch(`/api/platform/platform-users`, {
        method: "POST",
        body: {
          email: inviteDraft.email.trim().toLowerCase(),
          display_name: inviteDraft.display_name.trim(),
          role: inviteDraft.role,
          reason: inviteDraft.reason.trim(),
        },
      });
      setPendingInvite({
        email: data.admin.email,
        token: data.invitation.token,
        accept_url: data.invitation.accept_url,
      });
      setInviteDraft({ email: "", display_name: "", role: "support", reason: "" });
      setInviteOpen(false);
      await loadPlatformUsers();
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : "Failed to invite user.");
    } finally {
      setInviteBusy(false);
    }
  }

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
          <div style={{ marginBottom: 16, display: "flex", gap: 8, alignItems: "center" }}>
            {has("platform_user.manage") ? (
              <button
                type="button"
                style={{
                  padding: "6px 14px",
                  background: "#00D1C1",
                  color: "#000",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontWeight: 600,
                }}
                onClick={() => setInviteOpen(true)}
                disabled={inviteBusy}
              >
                {inviteBusy ? "Inviting…" : "Invite platform user"}
              </button>
            ) : null}
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

          {inviteError ? (
            <div style={{ color: "#EF4444", marginBottom: 8 }}>{inviteError}</div>
          ) : null}

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

          {pendingInvite ? (
            <div
              style={{
                marginTop: 24,
                padding: 16,
                border: "1px solid #00D1C1",
                background: "#E0F7F5",
                borderRadius: 6,
              }}
            >
              <h3 style={{ marginTop: 0 }}>Invitation created</h3>
              <p style={{ margin: "4px 0" }}>
                Invitation sent to <strong>{pendingInvite.email}</strong>.
              </p>
              <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
                Share this one-time link with the new admin:
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="text"
                  readOnly
                  value={pendingInvite.accept_url}
                  style={{
                    flex: 1,
                    padding: 6,
                    fontFamily: "monospace",
                    fontSize: 12,
                  }}
                />
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(pendingInvite.accept_url);
                    setPendingInvite(null);
                  }}
                  style={{
                    padding: "6px 12px",
                    background: "#00D1C1",
                    color: "#000",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                  }}
                >
                  Copy & close
                </button>
              </div>
              <p style={{ fontSize: 11, color: "#666", marginTop: 8 }}>
                The invite expires in 72 hours. The new admin sets their own password when they open the link.
              </p>
            </div>
          ) : null}

          {inviteOpen && has("platform_user.manage") ? (
            <div
              style={{
                marginTop: 24,
                padding: 16,
                border: "1px solid #d9dde5",
                background: "#F7F8FA",
                borderRadius: 6,
              }}
            >
              <h3 style={{ marginTop: 0 }}>Invite platform user</h3>
              <form onSubmit={handleInvite} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
                    Email
                  </label>
                  <input
                    type="email"
                    required
                    value={inviteDraft.email}
                    onChange={(e) =>
                      setInviteDraft({ ...inviteDraft, email: e.target.value })
                    }
                    placeholder="admin@yourcompany.com"
                    style={{
                      width: "100%",
                      padding: 6,
                      border: "1px solid #d9dde5",
                      borderRadius: 4,
                      boxSizing: "border-box",
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
                    Role
                  </label>
                  <select
                    value={inviteDraft.role}
                    onChange={(e) =>
                      setInviteDraft({ ...inviteDraft, role: e.target.value })
                    }
                    style={{
                      width: "100%",
                      padding: 6,
                      border: "1px solid #d9dde5",
                      borderRadius: 4,
                      boxSizing: "border-box",
                    }}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
                    Display name
                  </label>
                  <input
                    value={inviteDraft.display_name}
                    onChange={(e) =>
                      setInviteDraft({ ...inviteDraft, display_name: e.target.value })
                    }
                    placeholder="Jane Smith"
                    style={{
                      width: "100%",
                      padding: 6,
                      border: "1px solid #d9dde5",
                      borderRadius: 4,
                      boxSizing: "border-box",
                    }}
                  />
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
                    Reason
                  </label>
                  <textarea
                    required
                    value={inviteDraft.reason}
                    onChange={(e) =>
                      setInviteDraft({ ...inviteDraft, reason: e.target.value })
                    }
                    placeholder="Why is this admin being invited?"
                    rows={2}
                    style={{
                      width: "100%",
                      padding: 6,
                      border: "1px solid #d9dde5",
                      borderRadius: 4,
                      boxSizing: "border-box",
                    }}
                  />
                </div>
                <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8, marginTop: 8 }}>
                  <button
                    type="submit"
                    disabled={inviteBusy}
                    style={{
                      padding: "6px 14px",
                      background: "#00D1C1",
                      color: "#000",
                      border: "none",
                      borderRadius: 4,
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    {inviteBusy ? "Inviting…" : "Send invitation"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setInviteOpen(false);
                      setInviteError(null);
                    }}
                    style={{
                      padding: "6px 14px",
                      border: "1px solid #d9dde5",
                      background: "#fff",
                      borderRadius: 4,
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          ) : null}
        </>
      ) : (
        <p className="pf-muted" style={{ color: "red" }}>
          Access denied. <a href="/admin/login">Log in</a> as a platform admin.
        </p>
      )}
    </div>
  );
}


