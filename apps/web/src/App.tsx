import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { ThemeProvider } from "./styles/ThemeProvider";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import AcceptInvitationPage from "./pages/staff/AcceptInvitationPage";
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
import BranchesPage from "./pages/staff/BranchesPage";
import InventoryPage from "./pages/staff/InventoryPage";
import EmployeesPage from "./pages/staff/EmployeesPage";
import LoyaltyPage from "./pages/staff/LoyaltyPage";
import ReviewsPage from "./pages/staff/ReviewsPage";
import SubscriptionPage from "./pages/staff/SubscriptionPage";

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
    <ThemeProvider>
      <AuthProvider>
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/t/:qrToken" element={<CustomerMenuPage />} />
          <Route path="/status/:statusToken" element={<CustomerStatusPage />} />
          <Route path="/auth/invitations/:token" element={<AcceptInvitationPage />} />

          <Route path="/staff" element={<StaffLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="tables" element={<TablesPage />} />
            <Route path="tables/:tableId/order" element={<WaiterOrderPage />} />
            <Route path="pending" element={<PendingPage />} />
            <Route path="menu" element={<MenuManagePage />} />
            <Route path="payments" element={<PaymentSettingsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="branches" element={<BranchesPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="loyalty" element={<LoyaltyPage />} />
            <Route path="reviews" element={<ReviewsPage />} />
            <Route path="subscription" element={<SubscriptionPage />} />
          </Route>

          {/* Kitchen and cashier are stations, not dashboard pages: full-bleed shell. */}
          <Route element={<OpsLayout />}>
            <Route path="/staff/kitchen" element={<KitchenPage />} />
            <Route path="/staff/cashier" element={<CashierPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        <Route path="/admin/tenants/create" element={<AdminTenantCreatePage />} />
  <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
</Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}