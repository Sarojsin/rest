import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import CustomerMenuPage from "./pages/CustomerMenuPage";
import CustomerStatusPage from "./pages/CustomerStatusPage";
import StaffLayout from "./pages/staff/StaffLayout";
import TablesPage from "./pages/staff/TablesPage";
import PendingPage from "./pages/staff/PendingPage";
import KitchenPage from "./pages/staff/KitchenPage";
import CashierPage from "./pages/staff/CashierPage";
import MenuManagePage from "./pages/staff/MenuManagePage";
import ReportsPage from "./pages/staff/ReportsPage";
import WaiterOrderPage from "./pages/staff/WaiterOrderPage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/t/:qrToken" element={<CustomerMenuPage />} />
        <Route path="/status/:statusToken" element={<CustomerStatusPage />} />
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<Navigate to="tables" replace />} />
          <Route path="tables" element={<TablesPage />} />
          <Route path="tables/:tableId/order" element={<WaiterOrderPage />} />
          <Route path="pending" element={<PendingPage />} />
          <Route path="kitchen" element={<KitchenPage />} />
          <Route path="cashier" element={<CashierPage />} />
          <Route path="menu" element={<MenuManagePage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
