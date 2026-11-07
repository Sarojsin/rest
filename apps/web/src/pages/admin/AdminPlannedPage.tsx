import React, { useLocation } from "react-router-dom";

const TITLES: Record<string, string> = {
  "/tenants": "Tenants",
  "/plans": "Plans",
  "/subscriptions": "Subscriptions",
  "/invoices": "Invoices",
  "/payments": "Payments",
  "/refunds": "Refunds",
  "/platform-users": "Platform users",
  "/audit": "Audit log",
  "/settings": "Settings",
  "/diagnostics": "Diagnostics",
};

/**
 * Honest placeholder for platform modules that land with the billing milestone
 * (PA-1). Without it, the sidebar links fall through the catch-all route and
 * silently return to the dashboard.
 */
export default function AdminPlannedPage() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "Not available";

  return (
    <>
      <h1 style={{ marginTop: 0 }}>{title}</h1>
      <div className="pf-panel" style={{ marginTop: 20 }}>
        <h2>Not implemented yet</h2>
        <p className="pf-muted">
          This section arrives with the platform billing and tenant-management milestone (PA-1).
          It is listed in the navigation so the permission model can be verified, but no data is
          shown and no action is available yet.
        </p>
      </div>
    </>
  );
}


