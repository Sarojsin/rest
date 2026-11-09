import {
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useState } from "react";
import { PageHeader } from "../../../components/PageHeader";
import { useAuth } from "../../../lib/auth";
import { Icon } from "../../../components/Icon";

type Section = {
  to: string;
  label: string;
  icon: string;
  permission: string | null;
};

const SECTIONS: Section[] = [
  { to: "/staff/reports", label: "Overview", icon: "overview", permission: "reports.read" },
  { to: "/staff/reports/sales", label: "Sales detail", icon: "reports", permission: "reports.read" },
  { to: "/staff/reports/daily", label: "Daily trend", icon: "queue", permission: "reports.read" },
  { to: "/staff/reports/payments", label: "Payments", icon: "card", permission: "reports.read" },
  { to: "/staff/reports/inventory", label: "Inventory", icon: "inventory", permission: "inventory.read" },
  { to: "/staff/reports/kitchen", label: "Kitchen", icon: "staff", permission: "kitchen.read" },
  { to: "/staff/reports/audit", label: "Audit trail", icon: "search", permission: "audit.read" },
];

const SUB_TITLES: Record<string, string> = {
  Overview: "Sales & audit",
  "Sales detail": "Gross, collected, outstanding",
  "Daily trend": "Orders & sales per day",
  Payments: "Cash vs QR collected",
  Inventory: "Low stock & consumption",
  Kitchen: "Ticket prep speed",
  "Audit trail": "Append-only event log",
};

export default function ReportsLayout() {
  const { has } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const visible = SECTIONS.filter((s) => !s.permission || has(s.permission));
  const activeSection =
    visible.find((s) => pathname === s.to) ??
    visible.find((s) => pathname.startsWith(s.to + "/")) ??
    visible[0];

  if (pathname.startsWith("/staff/reports/") && pathname !== "/staff/reports/") {
    const rest = pathname.slice("/staff/reports/".length);
    const first = rest.split("/")[0];
    if (!visible.some((s) => s.to === "/staff/reports/" + first)) {
      navigate("/staff/reports", { replace: true });
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Reporting"
        title={activeSection.label}
        sub={SUB_TITLES[activeSection.label] ?? "Recorded server-side figures."}
        actions={
          <button className="btn secondary" type="button" onClick={() => window.location.reload()}>
            Refresh
          </button>
        }
      />

      <nav className="section-nav" aria-label="Report sections">
        {visible.length > 1 ? (
          <>
            <div className="section-nav-list">
              {visible.map((section) => (
                <NavLink
                  key={section.to}
                  to={section.to}
                  end={section.to === "/staff/reports"}
                  className={({ isActive }) =>
                    `section-link ${isActive ? "is-active" : ""}`
                  }
                  onClick={() => setMobileOpen(false)}
                >
                  <span className="section-icon">
                    <Icon name={section.icon as any} size={16} />
                  </span>
                  {section.label}
                </NavLink>
              ))}
            </div>
            <button
              className="btn ghost section-mobile-toggle"
              type="button"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((o) => !o)}
            >
              Sections {mobileOpen ? "▲" : "▼"}
            </button>
          </>
        ) : (
          <p className="muted text-sm">No report sections available.</p>
        )}
        {mobileOpen && visible.length > 1 ? (
          <div className="section-nav-mobile">
            {visible.map((section) => (
              <NavLink
                key={section.to}
                to={section.to}
                end={section.to === "/staff/reports"}
                className={({ isActive }) =>
                  `section-link-mobile ${isActive ? "is-active" : ""}`
                }
                onClick={() => setMobileOpen(false)}
              >
                <span className="section-icon">
                  <Icon name={section.icon as any} size={16} />
                </span>
                {section.label}
              </NavLink>
            ))}
          </div>
        ) : null}
      </nav>

      <main className="report-main">
        <Outlet />
      </main>
    </div>
  );
}
