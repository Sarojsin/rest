/**
 * Super Admin (platform console) entry point.
 *
 * This is a separate build entry from the tenant app: it never imports tenant
 * pages, tenant auth, or the tenant stylesheet. The only shared code is the
 * platform-neutral `@rest/api-client` package, which the admin app does not
 * currently need.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { PlatformAuthProvider } from "./lib/platformAuth";
import AdminGuard, { RequirePermission } from "./pages/admin/AdminGuard";
import AdminLoginPage from "./pages/admin/AdminLoginPage";
import AdminMfaPage from "./pages/admin/AdminMfaPage";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminTenantsPage from "./pages/admin/AdminTenantsPage";
import AdminPlansPage from "./pages/admin/AdminPlansPage";
import AdminSubscriptionsPage from "./pages/admin/AdminSubscriptionsPage";
import AdminInvoicesPage from "./pages/admin/AdminInvoicesPage";
import AdminPaymentsPage from "./pages/admin/AdminPaymentsPage";
import AdminRefundsPage from "./pages/admin/AdminRefundsPage";
import AdminPlatformUsersPage from "./pages/admin/AdminPlatformUsersPage";
import AdminAuditPage from "./pages/admin/AdminAuditPage";
import AdminSettingsPage from "./pages/admin/AdminSettingsPage";
import "./styles/admin.css";

/**
 * Local development keeps the `/admin` prefix on the shared Vite server
 * (PA-ADR-3). Production serves the admin app from the root of the admin
 * origin, so the basename is `/`.
 */
const basename = import.meta.env.DEV ? "/admin" : "/";

document.title = "Platform Console";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <PlatformAuthProvider>
        <Routes>
          <Route path="/login" element={<AdminLoginPage />} />
          <Route path="/mfa" element={<AdminMfaPage />} />
          <Route element={<AdminGuard />}>
            <Route element={<AdminLayout />}>
              <Route index element={<AdminDashboardPage />} />
              <Route
                path="/tenants"
                element={
                  <RequirePermission permission="tenant.view">
                    <AdminTenantsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/plans"
                element={
                  <RequirePermission permission="plan.view">
                    <AdminPlansPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/subscriptions"
                element={
                  <RequirePermission permission="subscription.view">
                    <AdminSubscriptionsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/invoices"
                element={
                  <RequirePermission permission="invoice.view">
                    <AdminInvoicesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/payments"
                element={
                  <RequirePermission permission="invoice.view">
                    <AdminPaymentsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/refunds"
                element={
                  <RequirePermission permission="payment.refund.approve">
                    <AdminRefundsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/platform-users"
                element={
                  <RequirePermission permission="platform_user.view">
                    <AdminPlatformUsersPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/audit"
                element={
                  <RequirePermission permission="audit.view">
                    <AdminAuditPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/settings"
                element={
                  <RequirePermission permission="settings.view">
                    <AdminSettingsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/diagnostics"
                element={
                  <RequirePermission permission="diagnostics.view">
                    <Navigate to="/admin" replace />
                  </RequirePermission>
                }
              />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </PlatformAuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);