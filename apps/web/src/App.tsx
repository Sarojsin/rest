import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { ThemeProvider } from "./styles/ThemeProvider";
import { setupForegroundListener } from "./lib/fcm";
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
  const [push, setPush] = useState<{ title: string; body: string } | null>(null);
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Create audio element once on mount
    const audioEl = new Audio("/notification.wav");
    audioEl.preload = "auto";
    audioEl.volume = 0.5;
    setAudio(audioEl);

    return () => {
      audioEl.pause();
      audioEl.src = "";
    };
  }, []);

  // Show an in-app toast when a push arrives while the tab is open.
  useEffect(() => {
    const unsubscribe = setupForegroundListener(({ title, body }) => {
      setPush({ title, body });
      window.setTimeout(() => setPush(null), 6000);
      
      // Play notification sound if user has interacted with the page
      if (audio) {
        try {
          audio.play().catch((err) => {
            // Silently ignore autoplay policy errors
            if (err.name !== "NotAllowedError") {
              console.debug("[App] Could not play notification sound:", err);
            }
          });
        } catch {
          // Ignore any other errors
        }
      }
    });
    return () => unsubscribe?.();
  }, [audio]);

  return (
    <ThemeProvider>
      <AuthProvider>
        <ScrollToTop />
        {push && (
          <div
            role="status"
            style={{
              position: "fixed",
              top: 16,
              right: 16,
              zIndex: 9999,
              maxWidth: 360,
              padding: "12px 16px",
              borderRadius: 10,
              background: "#0f1b2d",
              color: "#fff",
              boxShadow: "0 8px 24px rgba(0,0,0,.28)",
              fontSize: 14,
            }}
          >
            <strong style={{ display: "block", marginBottom: 2 }}>{push.title}</strong>
            <span style={{ opacity: 0.85 }}>{push.body}</span>
            <button
              type="button"
              onClick={() => setPush(null)}
              style={{
                position: "absolute",
                top: 4,
                right: 8,
                background: "transparent",
                border: 0,
                color: "#fff",
                fontSize: 16,
                cursor: "pointer",
              }}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        )}
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