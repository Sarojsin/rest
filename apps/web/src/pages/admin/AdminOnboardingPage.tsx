import { useEffect, useMemo, useState, type FormEvent } from "react";
import { usePlatformAuth, describePlatformError } from "../../lib/platformAuth";
import { PlatformApiError, platformFetch } from "../../lib/platformApi";

type Registration = {
  id: string;
  restaurant_name: string;
  restaurant_slug: string;
  owner_email: string;
  owner_name: string;
  owner_phone: string | null;
  plan_code: string;
  trial_days: number;
  status: string;
  created_at: string;
  reviewed_at: string | null;
  review_reason: string | null;
  restaurant_id: string | null;
};

type TenantRow = {
  tenant_id: string;
  name: string;
  slug: string;
  status: string;
  onboarding_stage: string;
  onboarding_completed_at: string | null;
  subscription_status: string | null;
  trial_ends_at: string | null;
  created_at: string;
};

type Plan = {
  code: string;
  name: string;
  status: string;
  trial_days: number;
  price_monthly_minor: number;
  currency_code: string;
};

type InvitationInfo = {
  email: string;
  link: string;
  sent: boolean | null;
  expiresAt: string | null;
};

type Tab = "PENDING" | "APPROVED" | "REJECTED" | "ALL";

const STAGE_LABELS: Record<string, string> = {
  registered: "Registered",
  approved: "Approved",
  invited: "Invited",
  mfa_setup: "MFA setup",
  onboarding_complete: "Complete",
  rejected: "Rejected",
};

function statusPill(status: string) {
  const styles: Record<string, { background: string; color: string }> = {
    PENDING: { background: "#fef3c7", color: "#92400e" },
    APPROVED: { background: "#dcfce7", color: "#166534" },
    REJECTED: { background: "#fee2e2", color: "#991b1b" },
    ACTIVE: { background: "#dcfce7", color: "#166534" },
    TRIALING: { background: "#dbeafe", color: "#1e40af" },
  };
  const style = styles[status] ?? { background: "#f1f5f9", color: "#475569" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 10,
        fontSize: 11,
        fontWeight: 600,
        ...style,
      }}
    >
      {status}
    </span>
  );
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function CopyableLink({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      const input = document.getElementById("invite-link-input") as HTMLInputElement | null;
      if (input) {
        input.select();
        document.execCommand("copy");
        setCopied(true);
      }
    }
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
      <input
        id="invite-link-input"
        readOnly
        value={value}
        onFocus={(event) => event.currentTarget.select()}
        style={{
          flex: 1,
          padding: "8px 10px",
          border: "1px solid #cbd5e1",
          borderRadius: 4,
          fontSize: 12,
          fontFamily: "monospace",
        }}
      />
      <button type="button" className="pf-button secondary" onClick={copy}>
        {copied ? "Copied" : "Copy link"}
      </button>
    </div>
  );
}

function ActionDialog({
  title,
  description,
  confirmWord,
  submitLabel,
  busy,
  error,
  onCancel,
  onSubmit,
}: {
  title: string;
  description: string;
  confirmWord: string;
  submitLabel: string;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (reason: string) => void;
}) {
  const [reason, setReason] = useState(description);
  const [typed, setTyped] = useState("");
  const ready = reason.trim().length > 0 && typed.trim() === confirmWord;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (ready) onSubmit(reason.trim());
  }

  return (
    <div className="pf-dialog-backdrop" role="presentation">
      <div className="pf-dialog" role="dialog" aria-modal="true" aria-labelledby="onboarding-action-title">
        <h2 id="onboarding-action-title" style={{ marginTop: 0 }}>
          {title}
        </h2>
        {error ? <div className="pf-error">{error}</div> : null}
        <form onSubmit={submit}>
          <div className="pf-field">
            <label htmlFor="action-reason">Reason</label>
            <input
              id="action-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              maxLength={1000}
            />
          </div>
          <div className="pf-field">
            <label htmlFor="action-confirm">
              Type <code>{confirmWord}</code> to confirm
            </label>
            <input
              id="action-confirm"
              value={typed}
              onChange={(event) => setTyped(event.target.value)}
              autoComplete="off"
            />
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" className="pf-button secondary" onClick={onCancel} disabled={busy}>
              Cancel
            </button>
            <button type="submit" className="pf-button" disabled={busy || !ready}>
              {busy ? "Working…" : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const EMPTY_FORM = {
  name: "",
  slug: "",
  ownerName: "",
  ownerEmail: "",
  ownerPhone: "",
  address: "",
  branchName: "Main Branch",
  branchCode: "MAIN",
  planCode: "",
  trialDays: "14",
  reason: "Admin onboarding",
};

export default function AdminOnboardingPage() {
  const { admin, loading: authLoading } = usePlatformAuth();

  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("PENDING");

  const [actionDialog, setActionDialog] = useState<{
    kind: "approve" | "reject";
    reg: Registration;
  } | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [invitation, setInvitation] = useState<InvitationInfo | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setLoadError(null);
    try {
      const [regs, onboarding, planList] = await Promise.all([
        platformFetch<{ items: Registration[] }>(
          "/api/platform/self-service/registrations?page=1&page_size=100"
        ),
        platformFetch<{ items: TenantRow[] }>(
          "/api/platform/onboarding?page=1&page_size=100"
        ),
        platformFetch<{ items: Plan[] }>("/api/platform/plans"),
      ]);
      setRegistrations(regs.items ?? []);
      setTenants(onboarding.items ?? []);
      const active = (planList.items ?? []).filter((plan) => plan.status === "ACTIVE");
      setPlans(active);
      setForm((current) =>
        current.planCode || active.length === 0
          ? current
          : {
              ...current,
              planCode: active[0].code,
              trialDays: String(active[0].trial_days ?? 14),
            }
      );
    } catch (error) {
      setLoadError(describePlatformError(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (admin || authLoading === false) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin, authLoading]);

  const counts = useMemo(
    () => ({
      PENDING: registrations.filter((item) => item.status === "PENDING").length,
      APPROVED: registrations.filter((item) => item.status === "APPROVED").length,
      REJECTED: registrations.filter((item) => item.status === "REJECTED").length,
      ALL: registrations.length,
    }),
    [registrations]
  );

  const visibleRegistrations =
    tab === "ALL"
      ? registrations
      : registrations.filter((item) => item.status === tab);

  function invitationLink(token: string): string {
    return `${window.location.origin}/auth/invitations/${token}`;
  }

  async function runAction(reason: string) {
    if (!actionDialog) return;
    const { kind, reg } = actionDialog;
    setActionBusy(true);
    setActionError(null);
    try {
      const result = await platformFetch<{
        owner_email?: string;
        invitation_token?: string | null;
        invitation_expires_at?: string | null;
      }>(
        `/api/platform/self-service/registrations/${reg.id}/${kind}`,
        {
          method: "POST",
          body: { confirm: reg.restaurant_slug, reason },
        }
      );

      if (kind === "approve" && result.invitation_token) {
        setInvitation({
          email: result.owner_email ?? reg.owner_email,
          link: invitationLink(result.invitation_token),
          sent: null,
          expiresAt: result.invitation_expires_at ?? null,
        });
      }
      setActionDialog(null);
      await loadData();
    } catch (error) {
      if (error instanceof PlatformApiError && error.code === "STEP_UP_REQUIRED") {
        setActionError(
          "Re-authentication required. Complete the dialog that just opened, then submit again."
        );
      } else {
        setActionError(describePlatformError(error));
      }
    } finally {
      setActionBusy(false);
    }
  }

  async function createRestaurant(event: FormEvent) {
    event.preventDefault();
    setCreateBusy(true);
    setCreateError(null);
    const slug = form.slug.trim() || slugify(form.name);
    try {
      const result = await platformFetch<{
        tenant_id: string;
        owner_invitation: {
          sent: boolean;
          email: string;
          accept_url: string;
          token: string;
          expires_at: string;
        };
      }>("/api/platform/onboarding/restaurants", {
        method: "POST",
        body: {
          restaurant: {
            name: form.name.trim(),
            legal_name: null,
            slug,
            contact_email: form.ownerEmail.trim(),
            contact_phone: form.ownerPhone.trim() || "0000000000",
            country: "NP",
            province: null,
            district: null,
            address: form.address.trim() || "Kathmandu, Nepal",
            website: null,
            timezone: "Asia/Kathmandu",
            currency_code: "NPR",
          },
          owner: {
            full_name: form.ownerName.trim(),
            email: form.ownerEmail.trim(),
            phone: form.ownerPhone.trim() || null,
          },
          subscription: {
            plan_code: form.planCode,
            trial_days: Number(form.trialDays) || 0,
            billing_interval: "MONTHLY",
          },
          branches: [
            {
              name: form.branchName.trim() || "Main Branch",
              code: form.branchCode.trim().toUpperCase() || "MAIN",
              address: form.address.trim() || null,
              phone: form.ownerPhone.trim() || null,
              email: null,
              opening_hours: null,
              timezone: "Asia/Kathmandu",
            },
          ],
          reason: form.reason.trim() || "Admin onboarding",
          confirm: slug,
        },
      });

      const invite = result.owner_invitation;
      setInvitation({
        email: invite.email,
        link: invite.accept_url || invitationLink(invite.token),
        sent: invite.sent,
        expiresAt: invite.expires_at,
      });
      setForm({ ...EMPTY_FORM, planCode: form.planCode, trialDays: form.trialDays });
      setShowCreate(false);
      await loadData();
    } catch (error) {
      if (error instanceof PlatformApiError && error.code === "STEP_UP_REQUIRED") {
        setCreateError(
          "Re-authentication required. Complete the dialog, then click Create restaurant again."
        );
      } else {
        setCreateError(describePlatformError(error));
      }
    } finally {
      setCreateBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Onboarding</h1>
        <p>Loading onboarding statuses…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginTop: 0, marginBottom: 4 }}>Onboarding</h1>
          <p className="pf-muted" style={{ marginTop: 0 }}>
            Track restaurant onboarding from registration to first order.
          </p>
        </div>
        <button
          type="button"
          className="pf-button"
          onClick={() => {
            setCreateError(null);
            setShowCreate((value) => !value);
          }}
        >
          {showCreate ? "Close form" : "Create restaurant"}
        </button>
      </div>

      {loadError ? <div className="pf-error">{loadError}</div> : null}

      {invitation ? (
        <div
          className="pf-panel"
          style={{
            marginTop: 16,
            padding: 16,
            border: "1px solid #bfdbfe",
            background: "#eff6ff",
            borderRadius: 6,
          }}
        >
          <strong>Owner invitation for {invitation.email}</strong>
          <p style={{ margin: "6px 0 0", fontSize: 13 }}>
            {invitation.sent === true
              ? "The invitation email was sent. You can also deliver this one-time link directly."
              : invitation.sent === false
                ? "Email delivery failed. Deliver this one-time link to the owner directly."
                : "Email delivery is not confirmed. Deliver this one-time link to the owner directly."}
            {invitation.expiresAt
              ? ` Expires ${new Date(invitation.expiresAt).toLocaleString()}.`
              : ""}
          </p>
          <CopyableLink value={invitation.link} />
          <div style={{ marginTop: 8 }}>
            <button
              type="button"
              className="pf-button secondary"
              onClick={() => setInvitation(null)}
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      {showCreate ? (
        <form
          onSubmit={createRestaurant}
          className="pf-panel"
          style={{ marginTop: 16, padding: 16, border: "1px solid #e2e8f0", borderRadius: 6 }}
        >
          <h2 style={{ marginTop: 0, fontSize: 16 }}>Create restaurant (admin onboarding)</h2>
          {createError ? <div className="pf-error">{createError}</div> : null}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <div className="pf-field">
              <label htmlFor="create-name">Restaurant name</label>
              <input
                id="create-name"
                required
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-slug">Slug (optional)</label>
              <input
                id="create-slug"
                value={form.slug}
                placeholder={slugify(form.name) || "auto-generated"}
                onChange={(event) =>
                  setForm((current) => ({ ...current, slug: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-owner-name">Owner full name</label>
              <input
                id="create-owner-name"
                required
                value={form.ownerName}
                onChange={(event) =>
                  setForm((current) => ({ ...current, ownerName: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-owner-email">Owner email</label>
              <input
                id="create-owner-email"
                type="email"
                required
                value={form.ownerEmail}
                onChange={(event) =>
                  setForm((current) => ({ ...current, ownerEmail: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-owner-phone">Owner phone</label>
              <input
                id="create-owner-phone"
                value={form.ownerPhone}
                onChange={(event) =>
                  setForm((current) => ({ ...current, ownerPhone: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-address">Address</label>
              <input
                id="create-address"
                value={form.address}
                placeholder="Kathmandu, Nepal"
                onChange={(event) =>
                  setForm((current) => ({ ...current, address: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-branch-name">Branch name</label>
              <input
                id="create-branch-name"
                value={form.branchName}
                onChange={(event) =>
                  setForm((current) => ({ ...current, branchName: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-branch-code">Branch code</label>
              <input
                id="create-branch-code"
                value={form.branchCode}
                onChange={(event) =>
                  setForm((current) => ({ ...current, branchCode: event.target.value }))
                }
              />
            </div>
            <div className="pf-field">
              <label htmlFor="create-plan">Plan</label>
              <select
                id="create-plan"
                required
                value={form.planCode}
                onChange={(event) => {
                  const code = event.target.value;
                  const plan = plans.find((item) => item.code === code);
                  setForm((current) => ({
                    ...current,
                    planCode: code,
                    trialDays: plan ? String(plan.trial_days ?? 14) : current.trialDays,
                  }));
                }}
              >
                <option value="">Select a plan…</option>
                {plans.map((plan) => (
                  <option key={plan.code} value={plan.code}>
                    {plan.name} ({plan.code})
                  </option>
                ))}
              </select>
            </div>
            <div className="pf-field">
              <label htmlFor="create-trial">Trial days</label>
              <input
                id="create-trial"
                type="number"
                min={0}
                max={365}
                value={form.trialDays}
                onChange={(event) =>
                  setForm((current) => ({ ...current, trialDays: event.target.value }))
                }
              />
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <button type="submit" className="pf-button" disabled={createBusy}>
              {createBusy ? "Creating…" : "Create restaurant & invite owner"}
            </button>
          </div>
        </form>
      ) : null}

      <h2 style={{ fontSize: 16, marginBottom: 4 }}>Self-service registrations</h2>
      <p className="pf-muted" style={{ marginTop: 0, fontSize: 12 }}>
        Owner-initiated applications awaiting review. Restaurants created by a platform admin
        appear under “Tenants in onboarding” below.
      </p>
      <div style={{ marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {(["PENDING", "APPROVED", "REJECTED", "ALL"] as Tab[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            style={{
              background: tab === key ? "var(--pf-color-primary)" : "transparent",
              color: tab === key ? "white" : "var(--pf-color-primary)",
              border: tab === key ? "none" : "1px solid var(--pf-color-primary)",
              borderRadius: 4,
              padding: "6px 12px",
              fontSize: 12,
              minWidth: 100,
            }}
          >
            {key === "ALL" ? "All" : key.charAt(0) + key.slice(1).toLowerCase()} ({counts[key]})
          </button>
        ))}
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8px" }}>Restaurant</th>
            <th style={{ padding: "12px 8px" }}>Owner email</th>
            <th style={{ padding: "12px 8px" }}>Plan</th>
            <th style={{ padding: "12px 8px" }}>Status</th>
            <th style={{ padding: "12px 8px" }}>Created</th>
            <th style={{ padding: "12px 8px" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {visibleRegistrations.length > 0 ? (
            visibleRegistrations.map((registration) => (
              <tr key={registration.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8px", fontWeight: 500 }}>
                  {registration.restaurant_name}
                  <div style={{ fontSize: 11, color: "#64748b" }}>{registration.restaurant_slug}</div>
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>{registration.owner_email}</td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>{registration.plan_code}</td>
                <td style={{ padding: "10px 8px" }}>{statusPill(registration.status)}</td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>
                  {new Date(registration.created_at).toLocaleDateString()}
                </td>
                <td style={{ padding: "10px 8px" }}>
                  {registration.status === "PENDING" ? (
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        type="button"
                        className="pf-button"
                        onClick={() => {
                          setActionError(null);
                          setActionDialog({ kind: "approve", reg: registration });
                        }}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="pf-button secondary"
                        onClick={() => {
                          setActionError(null);
                          setActionDialog({ kind: "reject", reg: registration });
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    <span style={{ fontSize: 12, color: "#64748b" }}>
                      {registration.review_reason || "—"}
                    </span>
                  )}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No {tab === "ALL" ? "" : tab.toLowerCase()} registrations found.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <h2 style={{ fontSize: 16, marginTop: 28, marginBottom: 8 }}>Tenants in onboarding</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8px" }}>Restaurant</th>
            <th style={{ padding: "12px 8px" }}>Slug / Tenant ID</th>
            <th style={{ padding: "12px 8px" }}>Stage</th>
            <th style={{ padding: "12px 8px" }}>Subscription</th>
            <th style={{ padding: "12px 8px" }}>Trial ends</th>
            <th style={{ padding: "12px 8px" }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {tenants.length > 0 ? (
            tenants.map((tenant) => (
              <tr key={tenant.tenant_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 8px", fontWeight: 500 }}>{tenant.name}</td>
                <td style={{ padding: "10px 8px", fontSize: 12, color: "#64748b" }}>
                  {tenant.slug}
                  <br />
                  <span style={{ fontSize: 11 }}>{tenant.tenant_id}</span>
                </td>
                <td style={{ padding: "10px 8px" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 10,
                      fontSize: 11,
                      background: "#f1f5f9",
                      color: "#475569",
                    }}
                  >
                    {STAGE_LABELS[tenant.onboarding_stage] || tenant.onboarding_stage || "—"}
                  </span>
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>
                  {tenant.subscription_status ? statusPill(tenant.subscription_status) : "—"}
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>
                  {tenant.trial_ends_at
                    ? new Date(tenant.trial_ends_at).toLocaleDateString()
                    : "—"}
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12 }}>
                  {new Date(tenant.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No tenants in onboarding yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {actionDialog ? (
        <ActionDialog
          title={actionDialog.kind === "approve" ? "Approve registration" : "Reject registration"}
          description={
            actionDialog.kind === "approve"
              ? "Approved by platform admin during onboarding review."
              : "Rejected by platform admin during onboarding review."
          }
          confirmWord={actionDialog.reg.restaurant_slug}
          submitLabel={actionDialog.kind === "approve" ? "Approve" : "Reject"}
          busy={actionBusy}
          error={actionError}
          onCancel={() => {
            setActionDialog(null);
            setActionError(null);
          }}
          onSubmit={runAction}
        />
      ) : null}
    </div>
  );
}
