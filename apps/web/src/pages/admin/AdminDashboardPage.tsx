import React, { usePlatformAuth } from "../../lib/platformAuth";

/**
 * PA-0 dashboard placeholder.
 *
 * Deliberately shows no fabricated metrics: the platform billing/tenant tables
 * land in PA-1. This page exists to prove the shell, guard, cookie session, and
 * permission-filtered navigation work end to end.
 */
export default function AdminDashboardPage() {
  const { admin, has } = usePlatformAuth();

  return (
    <>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      <p className="pf-muted" style={{ marginTop: 4 }}>
        Platform administration for every restaurant tenant. Tenant data is never rendered here
        beyond the fields the platform explicitly owns.
      </p>

      <div className="pf-grid" style={{ marginTop: 20 }}>
        <section className="pf-panel">
          <h2>Signed-in administrator</h2>
          <dl className="pf-kv">
            <dt>Name</dt>
            <dd>{admin?.display_name ?? "—"}</dd>
            <dt>Email</dt>
            <dd>{admin?.email ?? "—"}</dd>
            <dt>Role</dt>
            <dd>{admin?.role ?? "—"}</dd>
            <dt>MFA</dt>
            <dd>{admin?.mfa_enabled ? "Enabled" : "Not enabled"}</dd>
          </dl>
        </section>

        <section className="pf-panel">
          <h2>Foundation status</h2>
          <ul className="pf-list">
            <li>Separate platform identity realm</li>
            <li>HttpOnly cookie session with CSRF double-submit</li>
            <li>Mandatory MFA and step-up re-authentication</li>
            <li>Append-only platform audit log</li>
            <li>Tenant suspension gate with in-flight billing grace</li>
          </ul>
        </section>

        <section className="pf-panel">
          <h2>Coming next</h2>
          <p className="pf-muted">
            Tenant management, plans, subscriptions, invoices, and payments arrive with the
            platform billing milestone. This console intentionally contains no placeholder money
            figures.
          </p>
        </section>
      </div>

      {!has("platform.dashboard.view") ? (
        <div className="pf-notice" style={{ marginTop: 20 }}>
          Your role can sign in but does not include dashboard visibility. Use the navigation you
          are permitted to access.
        </div>
      ) : null}
    </>
  );
}


