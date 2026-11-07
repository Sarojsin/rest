import React, { Navigate, Outlet, useLocation } from "react-router-dom";
import { usePlatformAuth } from "../../lib/platformAuth";

export function AdminForbidden() {
  return (
    <div className="pf-panel">
      <h2>Forbidden</h2>
      <p className="pf-muted">
        Your platform role does not include permission for this page. If you believe this is
        wrong, ask a Super Admin to review your role.
      </p>
    </div>
  );
}

export function RequirePermission({
  permission,
  children,
}: {
  permission: string;
  children: React.ReactNode;
}) {
  const { has } = usePlatformAuth();
  if (!has(permission)) return <AdminForbidden />;
  return <>{children}</>;
}

export default function AdminGuard() {
  const { admin, loading, error } = usePlatformAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="pf-content">
        <div className="pf-panel">
          <p className="pf-muted">Verifying platform session…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pf-content">
        <div className="pf-panel">
          <h2>Could not verify the session</h2>
          <p className="pf-muted">{error}</p>
          <button
            type="button"
            className="pf-button"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}


