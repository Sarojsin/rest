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
  { to: "/staff/inventory", label: "Overview", icon: "overview", permission: "inventory.read" },
  { to: "/staff/inventory/ingredients", label: "Ingredients", icon: "inventory", permission: "inventory.read" },
  { to: "/staff/inventory/purchases", label: "Purchases", icon: "qr", permission: "inventory.read" },
  { to: "/staff/inventory/movements", label: "Movements", icon: "queue", permission: "inventory.read" },
  { to: "/staff/inventory/batches", label: "Batches", icon: "staff", permission: "inventory.read" },
  { to: "/staff/inventory/counts", label: "Stock counts", icon: "reports", permission: "inventory.read" },
  { to: "/staff/inventory/recipes", label: "Recipes", icon: "menu", permission: "inventory.read" },
  { to: "/staff/inventory/suppliers", label: "Suppliers", icon: "branches", permission: "inventory.read" },
];

export default function InventoryLayout() {
  const { has } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const visible = SECTIONS.filter((s) => !s.permission || has(s.permission));
  const activeSection =
    visible.find((s) => pathname === s.to) ??
    visible.find((s) => pathname.startsWith(s.to + "/")) ??
    visible[0];

  if (pathname.startsWith("/staff/inventory/") && pathname !== "/staff/inventory/") {
    const rest = pathname.slice("/staff/inventory/".length);
    const first = rest.split("/")[0];
    if (!visible.some((s) => s.to === "/staff/inventory/" + first)) {
      navigate("/staff/inventory", { replace: true });
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Inventory"
        title={activeSection.label}
        sub="Stock levels move only through recorded movements or received purchase orders, so every change leaves an audit trail."
        actions={
          <button className="btn secondary" type="button" onClick={() => window.location.reload()}>
            Refresh
          </button>
        }
      />

      {/* Section navigation — vertical on desktop, segmented on mobile */}
      <nav className="section-nav" aria-label="Inventory sections">
        {visible.length > 1 ? (
          <>
            <div className="section-nav-list">
              {visible.map((section) => (
                <NavLink
                  key={section.to}
                  to={section.to}
                  end={section.to === "/staff/inventory"}
                  className={({ isActive }) =>
                    `section-link ${isActive ? "is-active" : ""} ${section.icon ? "has-icon" : ""}`
                  }
                  onClick={() => setMobileOpen(false)}
                >
                  {section.icon ? (
                    <span className="section-icon">
                      <Icon name={section.icon as any} size={16} />
                    </span>
                  ) : null}
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
          <p className="muted text-sm">No inventory sections available.</p>
        )}
        {mobileOpen && visible.length > 1 ? (
          <div className="section-nav-mobile">
            {visible.map((section) => (
              <NavLink
                key={section.to}
                to={section.to}
                end={section.to === "/staff/inventory"}
                className={({ isActive }) =>
                  `section-link-mobile ${isActive ? "is-active" : ""}`
                }
                onClick={() => setMobileOpen(false)}
              >
                {section.icon ? (
                  <span className="section-icon">
                    <Icon name={section.icon as any} size={16} />
                  </span>
                ) : null}
                {section.label}
              </NavLink>
            ))}
          </div>
        ) : null}
      </nav>

      <main className="inventory-main">
        <Outlet />
      </main>
    </div>
  );
}
