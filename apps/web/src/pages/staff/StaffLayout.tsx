import { Navigate, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../lib/auth";

const LINKS = [
  { to: "/staff/tables", label: "Tables", permission: "orders.read" },
  { to: "/staff/pending", label: "QR queue", permission: "orders.confirm_qr" },
  { to: "/staff/kitchen", label: "Kitchen", permission: "kitchen.read" },
  { to: "/staff/cashier", label: "Cashier", permission: "bills.issue" },
  { to: "/staff/menu", label: "Menu", permission: "menu.manage" },
  { to: "/staff/reports", label: "Reports", permission: "reports.read" },
];

export default function StaffLayout() {
  const { me, loading, logout, has } = useAuth();
  if (loading) return <div className="shell">Loading...</div>;
  if (!me) return <Navigate to="/login" replace />;

  return (
    <div>
      <header className="staff-chrome">
        <div className="shell" style={{ paddingBottom: 8, paddingTop: 8 }}>
          <div className="topbar">
            <div className="brand">
              <div className="mark">HT</div>
              <div>
                <h1>{me.membership.restaurant_name}</h1>
                <p>{me.display_name} · {me.membership.role}</p>
              </div>
            </div>
            <nav className="nav">
              {LINKS.filter((link) => has(link.permission)).map((link) => (
                <NavLink key={link.to} to={link.to}>
                  {link.label}
                </NavLink>
              ))}
              <button className="ghost" onClick={logout} type="button">Sign out</button>
            </nav>
          </div>
        </div>
      </header>
      <div className="shell">
        <Outlet />
      </div>
    </div>
  );
}
