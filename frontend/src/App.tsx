import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme } from 'antd';
import esES from 'antd/locale/es_ES';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
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
import UserList from './pages/users/UserList';
import Settings from './pages/settings/Settings';
import Reports from './pages/reports/Reports';
import POList from './pages/purchases/POList';
import SunatPanel from './pages/sales/SunatPanel';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" />;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth();
  return isAdmin ? <>{children}</> : <Navigate to="/" />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/sales/:id/print" element={<ProtectedRoute><SalePrint /></ProtectedRoute>} />
      <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="sales" element={<SalesList />} />
        <Route path="sales/new" element={<SaleForm />} />
        <Route path="sales/:id" element={<SaleForm />} />
        <Route path="products" element={<ProductList />} />
        <Route path="clients" element={<ClientList />} />
        <Route path="inventory" element={<AdminRoute><StockLevels /></AdminRoute>} />
        <Route path="inventory/movements" element={<AdminRoute><Movements /></AdminRoute>} />
        <Route path="inventory/alerts" element={<AdminRoute><Alerts /></AdminRoute>} />
        <Route path="purchase-orders" element={<AdminRoute><POList /></AdminRoute>} />
        <Route path="sunat" element={<AdminRoute><SunatPanel /></AdminRoute>} />
        <Route path="users" element={<AdminRoute><UserList /></AdminRoute>} />
        <Route path="settings" element={<AdminRoute><Settings /></AdminRoute>} />
        <Route path="reports" element={<AdminRoute><Reports /></AdminRoute>} />
      </Route>
    </Routes>
  );
}

const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#3b6fd4',
    colorLink: '#5b8be6',
    colorError: '#e31e24',
    borderRadius: 6,
    fontFamily: "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    colorBgBase: '#0f1a2e',
    colorBgContainer: '#152038',
    colorBgElevated: '#1a2844',
    colorBgLayout: '#0a1220',
    colorBorder: '#1e3050',
    colorBorderSecondary: '#1a2844',
  },
  components: {
    Layout: { siderBg: '#091428', headerBg: '#152038' },
    Menu: { darkItemBg: '#091428', darkItemSelectedBg: '#1a3a8f', darkItemHoverBg: '#122d6e', darkSubMenuItemBg: '#060e1e' },
    Card: { colorBgContainer: '#152038', colorBorderSecondary: '#1e3050' },
    Table: { colorBgContainer: '#152038', headerBg: '#1a2844', rowHoverBg: '#1a2844' },
    Button: { primaryShadow: '0 2px 0 rgba(59, 111, 212, 0.2)' },
    Input: { colorBgContainer: '#1a2844' },
    Select: { colorBgContainer: '#1a2844' },
    Modal: { contentBg: '#152038', headerBg: '#152038' },
  },
};

const lightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1a3a8f',
    colorLink: '#1a3a8f',
    colorError: '#e31e24',
    borderRadius: 6,
    fontFamily: "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Layout: { siderBg: '#0a1e4a', headerBg: '#ffffff' },
    Menu: { darkItemBg: '#0a1e4a', darkItemSelectedBg: '#1a3a8f', darkItemHoverBg: '#122d6e', darkSubMenuItemBg: '#071738' },
    Button: { primaryShadow: '0 2px 0 rgba(26, 58, 143, 0.1)' },
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

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ThemedApp />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
