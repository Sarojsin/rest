import { useEffect, useRef, useState } from "react";
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { apiFetch, type Order, type ServiceCall } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Icon, type IconName } from "../../components/Icon";

/**
 * Header bell that pings staff wherever they are in the app (not only on the
 * QR queue screen): pending guest orders that need confirmation and open
 * service calls — guest "call waiter" taps and kitchen "food ready" signals.
 */
function NotificationBell() {
  const { has } = useAuth();
  const navigate = useNavigate();
  const [callCount, setCallCount] = useState(0);
  const [orderCount, setOrderCount] = useState(0);
  const [details, setDetails] = useState<ServiceCall[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const jobs: Promise<void>[] = [];
      jobs.push(
        apiFetch<ServiceCall[]>("/api/v1/service-calls?status=REQUESTED")
          .then((data) => {
            if (!cancelled) {
              setCallCount(data.length);
              setDetails(data);
            }
          })
          .catch(() => undefined)
      );
      if (has("orders.confirm_qr")) {
        jobs.push(
          apiFetch<Order[]>("/api/v1/orders?status=PENDING_CONFIRMATION")
            .then((data) => {
              if (!cancelled) setOrderCount(data.length);
            })
            .catch(() => undefined)
        );
      }
      await Promise.all(jobs);
    }
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [has]);

  const total = callCount + orderCount;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    const onClick = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <div className="alert-bell" ref={ref}>
      <button
        type="button"
        className={`alert-bell-button ${total > 0 ? "is-active" : ""}`}
        aria-label={
          total > 0
            ? `${total} alert${total === 1 ? "" : "s"}: open notification list`
            : "No open alerts"
        }
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span aria-hidden="true">🔔</span>
        {total > 0 ? <span className="alert-bell-count">{total}</span> : null}
      </button>
      {open ? (
        <div className="alert-bell-panel" role="region" aria-label="Notifications">
          {total === 0 ? <p className="muted">Nothing needs your attention right now.</p> : null}
          {orderCount > 0 ? (
            <button
              type="button"
              className="alert-bell-row"
              onClick={() => {
                setOpen(false);
                navigate("/staff/pending");
              }}
            >
              <span aria-hidden="true">🧾</span>
              <span>
                <strong>{orderCount}</strong> guest order{orderCount === 1 ? "" : "s"} awaiting your confirmation
              </span>
            </button>
          ) : null}
          {details
            .filter((call) => call.kind === "KITCHEN")
            .map((call) => (
              <button
                type="button"
                className="alert-bell-row"
                key={call.id}
                onClick={() => {
                  setOpen(false);
                  navigate("/staff/pending");
                }}
              >
                <span aria-hidden="true">🍽</span>
                <span>
                  <strong>{call.table_display_name}</strong> — food ready:{" "}
                  {call.items_summary || `ticket ${call.ticket_number ?? ""}`}
                </span>
              </button>
            ))}
          {details
            .filter((call) => call.kind !== "KITCHEN")
            .map((call) => (
              <button
                type="button"
                className="alert-bell-row"
                key={call.id}
                onClick={() => {
                  setOpen(false);
                  navigate("/staff/pending");
                }}
              >
                <span aria-hidden="true">🔔</span>
                <span>
                  <strong>{call.table_display_name}</strong> requests a waiter
                </span>
              </button>
            ))}
        </div>
      ) : null}
    </div>
  );
}

type NavItem = { to: string; label: string; icon: IconName; permissions: string[]; end?: boolean };

const NAV: NavItem[] = [
  { to: "/staff", label: "Overview", icon: "overview", permissions: ["reports.read", "orders.read"], end: true },
  { to: "/staff/tables", label: "Floor & QR", icon: "tables", permissions: ["orders.read"] },
  { to: "/staff/pending", label: "Order queue", icon: "queue", permissions: ["orders.confirm_qr"] },
  { to: "/staff/menu", label: "Menu", icon: "menu", permissions: ["menu.manage"] },
  { to: "/staff/payments", label: "Payment methods", icon: "qr", permissions: ["settings.manage"] },
  { to: "/staff/reports", label: "Reports", icon: "reports", permissions: ["reports.read"] },
];

const TITLES: Array<{ match: (path: string) => boolean; title: string; crumb: string }> = [
  { match: (p) => p === "/staff", title: "Overview", crumb: "Restaurant at a glance" },
  { match: (p) => p.startsWith("/staff/tables/"), title: "New order", crumb: "Floor" },
  { match: (p) => p === "/staff/tables", title: "Floor & QR codes", crumb: "Tables" },
  { match: (p) => p === "/staff/pending", title: "Order queue", crumb: "Confirm guest orders" },
  { match: (p) => p === "/staff/menu", title: "Menu management", crumb: "Categories & items" },
  { match: (p) => p === "/staff/payments", title: "Payment methods", crumb: "QR codes & cash" },
  { match: (p) => p === "/staff/reports", title: "Reports", crumb: "Sales & audit" },
];

export default function StaffLayout() {
  const { me, loading, logout, has } = useAuth();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!navOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNavOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [navOpen]);

  if (loading) {
    return (
      <div className="shell">
        <p className="muted">Loading staff workspace…</p>
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace />;

  const current =
    TITLES.find((entry) => entry.match(location.pathname)) ?? {
      title: "Staff",
      crumb: "Harbor Table",
    };

  const visible = NAV.filter((item) => item.permissions.some((permission) => has(permission)));

  return (
    <div className="app-shell" data-theme="management">
      <a className="skip-link" href="#staff-main">
        Skip to content
      </a>

      <div
        className={`app-backdrop ${navOpen ? "is-open" : ""}`}
        aria-hidden="true"
        onClick={() => setNavOpen(false)}
      />

      <aside className={`sidebar ${navOpen ? "is-open" : ""}`} aria-label="Staff navigation">
        <Link className="sidebar-brand" to="/staff">
          <div className="mark">HT</div>
          <div>
            <p className="sidebar-title">{me.membership.restaurant_name}</p>
            <p className="sidebar-role">{me.membership.role}</p>
          </div>
        </Link>

        <nav className="sidebar-nav">
          <p className="sidebar-label">Workspace</p>
          {visible.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link ${isActive ? "is-active" : ""}`}
            >
              <span className="sidebar-icon">
                <Icon name={item.icon} />
              </span>
              {item.label}
            </NavLink>
          ))}

          {has("kitchen.read") || has("bills.issue") ? (
            <>
              <p className="sidebar-label">Operations</p>
              {has("kitchen.read") ? (
                <NavLink
                  to="/staff/kitchen"
                  className={({ isActive }) => `sidebar-link ${isActive ? "is-active" : ""}`}
                >
                  <span className="sidebar-icon">
                    <Icon name="kitchen" />
                  </span>
                  Kitchen
                </NavLink>
              ) : null}
              {has("bills.issue") ? (
                <NavLink
                  to="/staff/cashier"
                  className={({ isActive }) => `sidebar-link ${isActive ? "is-active" : ""}`}
                >
                  <span className="sidebar-icon">
                    <Icon name="cashier" />
                  </span>
                  Cashier
                </NavLink>
              ) : null}
            </>
          ) : null}
        </nav>

        <div className="sidebar-foot">
          <div>
            <p className="sidebar-title">{me.display_name}</p>
            <p className="sidebar-role">{me.email}</p>
          </div>
          <button className="btn ghost btn-block" type="button" onClick={logout}>
            <Icon name="logout" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <button
            type="button"
            className="menu-toggle"
            aria-label="Open navigation"
            aria-expanded={navOpen}
            onClick={() => setNavOpen((open) => !open)}
          >
            <Icon name="bars" />
          </button>
          <div>
            <p className="app-topbar-crumb">{current.crumb}</p>
            <p className="app-topbar-title">{current.title}</p>
          </div>
          <div className="app-topbar-spacer" />
          {has("tables.manage") ? <NotificationBell /> : null}
        </header>

        <main className="app-content page" id="staff-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
