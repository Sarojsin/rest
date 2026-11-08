import { useCallback, useEffect, useState } from "react";
import { ApiError, apiFetch, type Branch } from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

type Membership = {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  created_at: string;
  branch_ids: string[];
};

type Seat = { current: number; limit: number | null; remaining: number | null };

type MembershipList = {
  items: Membership[];
  seats: Record<string, Seat> | null;
};

type InviteResponse = Membership & {
  invitation_token: string;
  invitation_expires_at: string;
};

type InviteState = {
  email: string;
  role: string;
  branchName: string;
  link: string;
  expiresAt: string;
};

const EMPTY_INVITE = {
  name: "",
  email: "",
  role: "waiter",
  branch_id: "",
};

const ROLE_OPTIONS = [
  { value: "manager", label: "Manager" },
  { value: "waiter", label: "Waiter" },
  { value: "kitchen", label: "Kitchen" },
  { value: "cashier", label: "Cashier" },
];

function roleBadge(role: string) {
  const tone = role === "owner" ? "good" : role === "manager" ? "info" : "neutral";
  return <span className={`badge ${tone}`}>{role}</span>;
}

function statusBadge(status: string) {
  const tone = status === "ACTIVE" ? "good" : status === "INVITED" ? "info" : "warn";
  return <span className={`badge ${tone}`}>{status.toLowerCase()}</span>;
}

export default function TeamPage() {
  const { has, me } = useAuth();
  const canManage = has("staff.manage");
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [seats, setSeats] = useState<Record<string, Seat> | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [draft, setDraft] = useState(EMPTY_INVITE);
  const [invited, setInvited] = useState<InviteState | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [list, branchList] = await Promise.all([
      apiFetch<MembershipList>("/api/v1/restaurant_memberships"),
      apiFetch<Branch[]>("/api/v1/branches"),
    ]);
    setMemberships(list.items);
    setSeats(list.seats);
    setBranches(branchList);
    setDraft((current) =>
      current.branch_id || branchList.length === 0
        ? current
        : { ...current, branch_id: branchList[0].id }
    );
  }, []);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof ApiError ? err.detail : "Could not load team accounts.")
    );
  }, [load]);

  async function invite(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await apiFetch<InviteResponse>("/api/v1/restaurant_memberships/invite", {
        method: "POST",
        body: JSON.stringify({
          email: draft.email.trim(),
          name: draft.name.trim(),
          role: draft.role,
          branch_id: draft.branch_id || null,
        }),
      });
      const branch = branches.find((entry) => entry.id === draft.branch_id);
      setInvited({
        email: created.email,
        role: created.role,
        branchName: branch?.name ?? "Unassigned",
        link: `${window.location.origin}/auth/invitations/${created.invitation_token}`,
        expiresAt: created.invitation_expires_at,
      });
      setCopied(false);
      setDraft((current) => ({ ...EMPTY_INVITE, branch_id: current.branch_id }));
      setNotice(`Invitation created for ${created.email}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create the invitation.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(membership: Membership) {
    if (membership.role === "owner") return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/restaurant_memberships/${membership.id}`, { method: "DELETE" });
      setNotice(`${membership.email} was removed from the team.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not remove that team member.");
    } finally {
      setBusy(false);
    }
  }

  async function copyLink() {
    if (!invited) return;
    try {
      await navigator.clipboard.writeText(invited.link);
      setCopied(true);
    } catch {
      const input = document.getElementById("team-invite-link") as HTMLInputElement | null;
      input?.select();
      document.execCommand("copy");
      setCopied(true);
    }
    window.setTimeout(() => setCopied(false), 2000);
  }

  function branchNames(ids: string[]): string {
    if (ids.length === 0) return "All branches";
    return ids
      .map((id) => branches.find((branch) => branch.id === id)?.name ?? "branch")
      .join(", ");
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Staff"
        title="Team accounts"
        sub="Create branch-scoped login accounts for managers, waiters, kitchen and cashier staff. Each person sets their own password from a one-time invitation link."
        actions={
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      {invited ? (
        <section
          className="section-card"
          aria-label="Invitation link"
          style={{ borderColor: "#bfdbfe", background: "#eff6ff" }}
        >
          <div className="section-card-head">
            <h3>Invitation for {invited.email}</h3>
            <span className="muted text-sm">
              {invited.role} · {invited.branchName}
            </span>
          </div>
          <div className="section-card-body">
            <p className="muted text-sm" style={{ marginTop: 0 }}>
              Send this one-time link to the staff member. It expires{" "}
              {new Date(invited.expiresAt).toLocaleString()} and can be used once. They choose
              their own password when they open it.
            </p>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                id="team-invite-link"
                readOnly
                value={invited.link}
                onFocus={(event) => event.currentTarget.select()}
                style={{
                  flex: 1,
                  minWidth: 260,
                  padding: "8px 10px",
                  border: "1px solid #cbd5e1",
                  borderRadius: 4,
                  fontFamily: "monospace",
                  fontSize: 12,
                }}
              />
              <button type="button" className="btn" onClick={() => void copyLink()}>
                {copied ? "Copied" : "Copy link"}
              </button>
              <button type="button" className="btn ghost" onClick={() => setInvited(null)}>
                Dismiss
              </button>
            </div>
          </div>
        </section>
      ) : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="team-title">
          <div className="section-card-head">
            <h3 id="team-title">Accounts</h3>
            <span className="muted text-sm">{memberships.length} on the team</span>
          </div>
          <div className="section-card-body">
            {memberships.length === 0 ? <p className="muted">No team accounts yet.</p> : null}
            {memberships.map((membership) => (
              <div className="audit-row" key={membership.id}>
                <div>
                  <strong>{membership.display_name || membership.email}</strong>{" "}
                  {roleBadge(membership.role)} {statusBadge(membership.status)}
                  <div className="muted text-sm">
                    {membership.email} · {branchNames(membership.branch_ids)}
                  </div>
                </div>
                {canManage &&
                membership.role !== "owner" &&
                membership.user_id !== me?.id ? (
                  <button
                    className="btn ghost btn-sm"
                    type="button"
                    disabled={busy}
                    onClick={() => void revoke(membership)}
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </section>

        <section className="section-card" aria-labelledby="invite-title">
          <div className="section-card-head">
            <h3 id="invite-title">Add a team account</h3>
            {seats ? <span className="muted text-sm">Seats: plan-managed</span> : null}
          </div>
          <div className="section-card-body">
            {canManage ? (
              <form className="stack" onSubmit={(event) => void invite(event)}>
                <div className="grid two">
                  <label className="field">
                    Full name
                    <input
                      value={draft.name}
                      onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                      placeholder="e.g. Sita Gurung"
                    />
                  </label>
                  <label className="field">
                    Email
                    <input
                      type="email"
                      required
                      value={draft.email}
                      onChange={(event) => setDraft({ ...draft, email: event.target.value })}
                      placeholder="staff@example.com"
                    />
                  </label>
                  <label className="field">
                    Role
                    <select
                      value={draft.role}
                      onChange={(event) => setDraft({ ...draft, role: event.target.value })}
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Branch
                    <select
                      required
                      value={draft.branch_id}
                      onChange={(event) => setDraft({ ...draft, branch_id: event.target.value })}
                    >
                      <option value="">Select a branch…</option>
                      {branches.map((branch) => (
                        <option key={branch.id} value={branch.id}>
                          {branch.name}
                          {branch.code ? ` (${branch.code})` : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <p className="muted text-sm" style={{ margin: 0 }}>
                  Managers see the whole restaurant. Waiter, kitchen and cashier accounts are
                  scoped to the selected branch.
                </p>
                <button
                  className="btn"
                  type="submit"
                  disabled={busy || !draft.email.trim() || !draft.branch_id}
                >
                  {busy ? "Creating…" : "Create invitation"}
                </button>
              </form>
            ) : (
              <p className="muted">You do not have permission to manage team accounts.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
