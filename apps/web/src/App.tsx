import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import CustomerMenuPage from "./pages/CustomerMenuPage";
import CustomerStatusPage from "./pages/CustomerStatusPage";
import StaffLayout from "./pages/staff/StaffLayout";
import OpsLayout from "./pages/staff/OpsLayout";
import OverviewPage from "./pages/staff/OverviewPage";
import TablesPage from "./pages/staff/TablesPage";
import PendingPage from "./pages/staff/PendingPage";
import KitchenPage from "./pages/staff/KitchenPage";
import CashierPage from "./pages/staff/CashierPage";
import MenuManagePage from "./pages/staff/MenuManagePage";
import PaymentSettingsPage from "./pages/staff/PaymentSettingsPage";
import ReportsPage from "./pages/staff/ReportsPage";
import WaiterOrderPage from "./pages/staff/WaiterOrderPage";

/**
 * SPA navigation keeps the previous scroll offset by default, which lands staff
 * mid-page on every route change. Reset to the top whenever the path changes.
 */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <AuthProvider>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/t/:qrToken" element={<CustomerMenuPage />} />
        <Route path="/status/:statusToken" element={<CustomerStatusPage />} />

        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="tables" element={<TablesPage />} />
          <Route path="tables/:tableId/order" element={<WaiterOrderPage />} />
          <Route path="pending" element={<PendingPage />} />
          <Route path="menu" element={<MenuManagePage />} />
          <Route path="payments" element={<PaymentSettingsPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>

        {/* Kitchen and cashier are stations, not dashboard pages: full-bleed shell. */}
        <Route element={<OpsLayout />}>
          <Route path="/staff/kitchen" element={<KitchenPage />} />
          <Route path="/staff/cashier" element={<CashierPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
