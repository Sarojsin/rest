import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { STEP_UP_EVENT, platformFetch } from "../../lib/platformApi";
import { describePlatformError, usePlatformAuth } from "../../lib/platformAuth";

const NAV = [
  { to: "/", label: "Dashboard", permission: "platform.dashboard.view", end: true },
  { to: "/tenants", label: "Tenants", permission: "tenant.view" },
  { to: "/onboarding", label: "Onboarding", permission: "onboarding.view" },
  { to: "/usage", label: "Usage & Limits", permission: "tenant.view" },
  { to: "/support", label: "Support", permission: "tenant.view" },
  { to: "/analytics", label: "Analytics", permission: "analytics.view" },
  { to: "/plans", label: "Plans", permission: "plan.view" },
  
  { to: "/subscriptions", label: "Subscriptions", permission: "subscription.view" },
  { to: "/invoices", label: "Invoices", permission: "invoice.view" },
  { to: "/payments", label: "Payments", permission: "invoice.view" },
  { to: "/refunds", label: "Refunds", permission: "payment.refund.approve" },
  { to: "/platform-users", label: "Platform users", permission: "platform_user.view" },
  { to: "/audit", label: "Audit log", permission: "audit.view" },
  { to: "/settings", label: "Settings", permission: "settings.view" },
  { to: "/diagnostics", label: "Diagnostics", permission: "diagnostics.view" },
];

function environmentLabel(): string {
  const configured = import.meta.env.VITE_PLATFORM_ENV;
  if (configured) return configured.toUpperCase();
  return import.meta.env.DEV ? "LOCAL" : "PRODUCTION";
}

function StepUpDialog({ onClose }: { onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await platformFetch("/api/platform/auth/step-up", {
        method: "POST",
        body: { password, code: code.trim() },
      });
      onClose();
    } catch (err) {
      setError(describePlatformError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pf-dialog-backdrop" role="presentation">
      <div className="pf-dialog" role="dialog" aria-modal="true" aria-labelledby="pf-stepup-title">
        <h2 id="pf-stepup-title" style={{ marginTop: 0 }}>
          Re-authenticate
        </h2>
        <p className="pf-muted">
          This action needs a fresh identity check. Confirm your password and authenticator code.
        </p>

        {error ? <div className="pf-error">{error}</div> : null}

        <form onSubmit={onSubmit}>
          <div className="pf-field">
            <label htmlFor="stepup-password">Password</label>
            <input
              id="stepup-password"
              type="password"
              autoComplete="current-password"
              autoFocus
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <div className="pf-field">
            <label htmlFor="stepup-code">Authenticator code</label>
            <input
              id="stepup-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              maxLength={32}
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" className="pf-button secondary" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button type="submit" className="pf-button" disabled={busy}>
              {busy ? "Verifying…" : "Verify"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminLayout() {
  const { admin, has, logout } = usePlatformAuth();
  const navigate = useNavigate();
  const [stepUpOpen, setStepUpOpen] = useState(false);
  const [stepUpNotice, setStepUpNotice] = useState(false);

  useEffect(() => {
    function onStepUpRequired() {
      setStepUpNotice(false);
      setStepUpOpen(true);
    }
    window.addEventListener(STEP_UP_EVENT, onStepUpRequired);
    return () => window.removeEventListener(STEP_UP_EVENT, onStepUpRequired);
  }, []);

  if (!admin) return null;

  const env = environmentLabel();
  // Super admins have all permissions; filter navigation based on permissions
  const visible = NAV.filter((item) => has(item.permission));

  async function onLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="pf-shell">
      <aside className="pf-sidebar">
        <div className="pf-brand">
          Platform Console
          <small>Super Admin</small>
        </div>
        <nav className="pf-nav" aria-label="Platform">
          {visible.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="pf-sidebar-foot">
          {admin.role} · MFA {admin.mfa_enabled ? "enabled" : "not enabled"}
        </div>
      </aside>

      <div className="pf-main">
        <header className="pf-topbar">
          <span className={`pf-env ${env === "PRODUCTION" ? "production" : "local"}`}>{env}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span className="pf-muted">
              {admin.display_name} · {admin.email}
            </span>
            <button type="button" className="pf-button secondary" onClick={onLogout}>
              Sign out
            </button>
          </div>
        </header>

        <main className="pf-content">
          {stepUpNotice ? (
            <div className="pf-notice">
              Identity re-verified. The original action was not repeated; submit it again.
            </div>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}