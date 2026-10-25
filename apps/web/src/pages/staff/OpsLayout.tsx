import { useEffect, useState } from "react";
import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { Icon } from "../../components/Icon";

/**
 * Full-bleed operational shell for kitchen and cashier screens.
 * Deliberately excludes the management sidebar and decorative chrome.
 */
export default function OpsLayout() {
  const { me, loading, logout, has } = useAuth();
  const location = useLocation();
  const [now, setNow] = useState(() => new Date());
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 20_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      // The browser may refuse (permissions, iOS Safari); the screen still works.
    }
  }

  if (loading) {
    return (
      <div className="shell">
        <p className="muted">Loading station…</p>
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace />;

  const isKitchen = location.pathname.includes("/kitchen");
  const title = isKitchen ? "Kitchen board" : "Cashier";
  const canManage = has("reports.read") || has("orders.read") || has("menu.manage");

  return (
    <div className="ops-shell" data-theme="operations">
      <a className="skip-link" href="#ops-main">
        Skip to content
      </a>
      <header className="ops-header">
        <div className="ops-header-inner">
          <div className="ops-brand">
            <div className="mark">HT</div>
            <div>
              <h1 className="ops-title">{title}</h1>
              <p className="ops-sub">
                {me.membership.restaurant_name} · {me.membership.role}
              </p>
            </div>
          </div>

          <div className="ops-meta">
            <span className="ops-clock">
              {now.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}
              {" · "}
              {now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
            </span>
            <div className="ops-actions">
              {canManage ? (
                <Link className="btn ghost" to="/staff">
                  Dashboard
                </Link>
              ) : null}
              <button className="btn ghost" type="button" onClick={() => void toggleFullscreen()}>
                <Icon name="expand" />
                {isFullscreen ? "Exit full screen" : "Full screen"}
              </button>
              <button className="btn ghost" type="button" onClick={logout}>
                <Icon name="logout" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="ops-body" id="ops-main">
        <Outlet />
      </main>
    </div>
  );
}
