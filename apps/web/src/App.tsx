import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { ThemeProvider } from "./styles/ThemeProvider";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import AcceptInvitationPage from "./pages/staff/AcceptInvitationPage";
import AdminDiagnosticsPage from "./pages/admin/AdminDiagnosticsPage";
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
import ReportsLayout from "./pages/staff/reports/ReportsLayout";
import ReportsOverviewPage from "./pages/staff/reports/ReportsOverviewPage";
import ReportsSalesPage from "./pages/staff/reports/ReportsSalesPage";
import ReportsDailyPage from "./pages/staff/reports/ReportsDailyPage";
import ReportsPaymentsPage from "./pages/staff/reports/ReportsPaymentsPage";
import ReportsInventoryPage from "./pages/staff/reports/ReportsInventoryPage";
import ReportsKitchenPage from "./pages/staff/reports/ReportsKitchenPage";
import ReportsAuditPage from "./pages/staff/reports/ReportsAuditPage";
import WaiterOrderPage from "./pages/staff/WaiterOrderPage";
import BranchesPage from "./pages/staff/BranchesPage";
import InventoryLayout from "./pages/staff/inventory/InventoryLayout";
import InventoryOverviewPage from "./pages/staff/inventory/InventoryOverviewPage";
import IngredientsPage from "./pages/staff/inventory/IngredientsPage";
import MovementsPage from "./pages/staff/inventory/MovementsPage";
import PurchaseOrdersPage from "./pages/staff/inventory/PurchaseOrdersPage";
import BatchesPage from "./pages/staff/inventory/BatchesPage";
import StockCountsPage from "./pages/staff/inventory/StockCountsPage";
import RecipesPage from "./pages/staff/inventory/RecipesPage";
import SuppliersPage from "./pages/staff/inventory/SuppliersPage";
import EmployeesPage from "./pages/staff/EmployeesPage";
import TeamPage from "./pages/staff/TeamPage";
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
            <Route path="reports" element={<ReportsLayout />}>
              <Route index element={<ReportsOverviewPage />} />
              <Route path="sales" element={<ReportsSalesPage />} />
              <Route path="daily" element={<ReportsDailyPage />} />
              <Route path="payments" element={<ReportsPaymentsPage />} />
              <Route path="inventory" element={<ReportsInventoryPage />} />
              <Route path="kitchen" element={<ReportsKitchenPage />} />
              <Route path="audit" element={<ReportsAuditPage />} />
            </Route>
            <Route path="branches" element={<BranchesPage />} />
            <Route path="inventory" element={<InventoryLayout />}>
              <Route index element={<InventoryOverviewPage />} />
              <Route path="ingredients" element={<IngredientsPage />} />
              <Route path="purchases" element={<PurchaseOrdersPage />} />
              <Route path="movements" element={<MovementsPage />} />
              <Route path="batches" element={<BatchesPage />} />
              <Route path="counts" element={<StockCountsPage />} />
              <Route path="recipes" element={<RecipesPage />} />
              <Route path="suppliers" element={<SuppliersPage />} />
            </Route>
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="team" element={<TeamPage />} />
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
          <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}