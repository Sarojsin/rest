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
import AdminGuard from "./pages/admin/AdminGuard";
import AdminLoginPage from "./pages/admin/AdminLoginPage";
import AdminMfaPage from "./pages/admin/AdminMfaPage";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import "./styles/admin.css";

/**
 * Local development keeps the `/admin` prefix on the shared Vite server
 * (PA-ADR-003). Production serves the admin app from the root of the admin
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
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </PlatformAuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
