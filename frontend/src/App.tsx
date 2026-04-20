import { useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme } from 'antd';
import esES from 'antd/locale/es_ES';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import ErrorBoundary from './components/ErrorBoundary';
import AppLayout from './components/Layout/AppLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import SalesList from './pages/sales/SalesList';
import SaleForm from './pages/sales/SaleForm';
import SalePrint from './pages/sales/SalePrint';
import ProductList from './pages/products/ProductList';
import ClientList from './pages/clients/ClientList';
import StockLevels from './pages/inventory/StockLevels';
import Movements from './pages/inventory/Movements';
import Alerts from './pages/inventory/Alerts';
import StockValorizado from './pages/inventory/StockValorizado';
import Kardex from './pages/inventory/Kardex';
import UserList from './pages/users/UserList';
import Settings from './pages/settings/Settings';
import Reports from './pages/reports/Reports';
import POList from './pages/purchases/POList';
import SmartRestock from './pages/purchases/SmartRestock';
import CatPage from './pages/cat/CatPage';
import CuentasPorPagar from './pages/purchases/CuentasPorPagar';
import SunatPanel from './pages/sales/SunatPanel';
import NotaCreditoForm from './pages/sales/NotaCreditoForm';
import ChatHistory from './pages/chat/ChatHistory';
import TrabajadorList from './pages/trabajadores/TrabajadorList';
import AsistenciaPage from './pages/trabajadores/AsistenciaPage';
import OnlineOrderList from './pages/online-orders/OnlineOrderList';
import WebChatLogs from './pages/online-orders/WebChatLogs';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1 },
    mutations: { retry: false },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" />;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth();
  return isAdmin ? <>{children}</> : <Navigate to="/sales" />;
}

function DefaultRedirect() {
  const { isAdmin } = useAuth();
  return isAdmin ? <Dashboard /> : <Navigate to="/sales" />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/sales/:id/print" element={<ProtectedRoute><SalePrint /></ProtectedRoute>} />
      <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<DefaultRedirect />} />
        <Route path="sales" element={<SaleForm />} />
        <Route path="sales/list" element={<SalesList />} />
        <Route path="sales/new" element={<SaleForm />} />
        <Route path="sales/nota-credito/new" element={<AdminRoute><NotaCreditoForm /></AdminRoute>} />
        <Route path="sales/:id" element={<SaleForm />} />
        <Route path="products" element={<ProductList />} />
        <Route path="clients" element={<ClientList />} />
        <Route path="inventory" element={<AdminRoute><StockLevels /></AdminRoute>} />
        <Route path="inventory/movements" element={<AdminRoute><Movements /></AdminRoute>} />
        <Route path="inventory/alerts" element={<Alerts />} />
        <Route path="inventory/stock-valorizado" element={<AdminRoute><StockValorizado /></AdminRoute>} />
        <Route path="inventory/kardex" element={<AdminRoute><Kardex /></AdminRoute>} />
        <Route path="purchase-orders" element={<AdminRoute><POList /></AdminRoute>} />
        <Route path="purchase-orders/restock" element={<AdminRoute><SmartRestock /></AdminRoute>} />
        <Route path="cat" element={<CatPage />} />
        <Route path="cuentas-por-pagar" element={<AdminRoute><CuentasPorPagar /></AdminRoute>} />
        <Route path="sunat" element={<AdminRoute><SunatPanel /></AdminRoute>} />
        <Route path="trabajadores" element={<AdminRoute><TrabajadorList /></AdminRoute>} />
        <Route path="trabajadores/asistencia" element={<AdminRoute><AsistenciaPage /></AdminRoute>} />
        <Route path="users" element={<AdminRoute><UserList /></AdminRoute>} />
        <Route path="settings" element={<AdminRoute><Settings /></AdminRoute>} />
        <Route path="reports" element={<AdminRoute><Reports /></AdminRoute>} />
        <Route path="online-orders" element={<OnlineOrderList />} />
        <Route path="web-chat-logs" element={<AdminRoute><WebChatLogs /></AdminRoute>} />
        <Route path="chat-history" element={<AdminRoute><ChatHistory /></AdminRoute>} />
      </Route>
    </Routes>
  );
}

/*
 * KTI POS Design System — Glassmorphism + OLED Dark
 * Brand: Red #c62828 / Blue #1a3a8f
 * Font: DM Sans (Google Fonts)
 * Style: Frosted glass cards, deep dark bg, green positive indicators
 */
const FONT = "'DM Sans', 'Segoe UI', Roboto, sans-serif";

const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#c62828',
    colorLink: '#60a5fa',
    colorError: '#f87171',
    colorSuccess: '#34d399',
    colorWarning: '#fbbf24',
    borderRadius: 10,
    fontFamily: FONT,
    colorBgBase: '#06080f',
    colorBgContainer: 'rgba(15, 23, 42, 0.6)',
    colorBgElevated: 'rgba(22, 33, 56, 0.8)',
    colorBgLayout: '#040609',
    colorBorder: 'rgba(255, 255, 255, 0.06)',
    colorBorderSecondary: 'rgba(255, 255, 255, 0.04)',
  },
  components: {
    Layout: { siderBg: 'rgba(6, 8, 15, 0.85)', headerBg: 'rgba(15, 23, 42, 0.6)' },
    Menu: { darkItemBg: 'transparent', darkItemSelectedBg: 'rgba(198, 40, 40, 0.18)', darkItemHoverBg: 'rgba(255, 255, 255, 0.05)', darkSubMenuItemBg: 'transparent' },
    Card: { colorBgContainer: 'rgba(15, 23, 42, 0.5)', colorBorderSecondary: 'rgba(255,255,255,0.06)' },
    Table: { colorBgContainer: 'rgba(15, 23, 42, 0.4)', headerBg: 'rgba(15, 23, 42, 0.7)', rowHoverBg: 'rgba(255, 255, 255, 0.03)' },
    Button: { primaryShadow: '0 4px 14px rgba(198, 40, 40, 0.3)' },
    Input: { colorBgContainer: 'rgba(255, 255, 255, 0.04)', activeBorderColor: '#c62828', hoverBorderColor: 'rgba(198, 40, 40, 0.4)' },
    Select: { colorBgContainer: 'rgba(255, 255, 255, 0.04)' },
    InputNumber: { colorBgContainer: 'rgba(255, 255, 255, 0.04)' },
    Modal: { contentBg: 'rgba(15, 23, 42, 0.95)', headerBg: 'rgba(15, 23, 42, 0.95)' },
    Statistic: { titleFontSize: 13 },
  },
};

const lightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#c62828',
    colorLink: '#1a3a8f',
    colorError: '#ef4444',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    borderRadius: 10,
    fontFamily: FONT,
  },
  components: {
    Layout: { siderBg: 'transparent', headerBg: 'rgba(255, 255, 255, 0.7)', bodyBg: '#f0f2f5' },
    Menu: { darkItemBg: 'transparent', darkItemSelectedBg: 'rgba(255,255,255,0.2)', darkItemHoverBg: 'rgba(255,255,255,0.1)', darkSubMenuItemBg: 'transparent' },
    Button: { primaryShadow: '0 4px 14px rgba(198, 40, 40, 0.2)' },
    Card: { colorBorderSecondary: '#e8ecf2' },
    Table: { rowHoverBg: 'rgba(198, 40, 40, 0.03)' },
    Statistic: { titleFontSize: 13 },
  },
};

function ThemedApp() {
  const { isDark } = useTheme();
  return (
    <ConfigProvider locale={esES} theme={isDark ? darkTheme : lightTheme}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  );
}

/** Poll /version.json every 60s — auto-reload when a new build is deployed */
function useAutoReload() {
  const knownVersion = useRef<string | null>(null);
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/version.json?t=' + Date.now());
        const { v } = await res.json();
        if (knownVersion.current === null) {
          knownVersion.current = v;
        } else if (v !== knownVersion.current) {
          window.location.reload();
        }
      } catch { /* ignore fetch errors */ }
    };
    check();
    const id = setInterval(check, 60_000);
    return () => clearInterval(id);
  }, []);
}

export default function App() {
  useAutoReload();
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ThemedApp />
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
