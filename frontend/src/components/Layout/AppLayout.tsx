import { useState, useEffect, useRef } from 'react';
import { Layout, Menu, Button, Dropdown, Space, Badge, theme } from 'antd';
import {
  DashboardOutlined,
  ShoppingCartOutlined,
  AppstoreOutlined,
  InboxOutlined,
  TeamOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BarChartOutlined,
  ShoppingOutlined,
  SunOutlined,
  MoonOutlined,
  CloudUploadOutlined,
  MessageOutlined,
  IdcardOutlined,
  GlobalOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { getOnlineOrderStats } from '../../api/onlineOrders';
import ChatWidget from '../Chat/ChatWidget';

/** Wrapper that fades+slides content on every route change */
function AnimatedOutlet() {
  const location = useLocation();
  const [visible, setVisible] = useState(true);
  const prevPath = useRef(location.pathname);

  useEffect(() => {
    if (location.pathname !== prevPath.current) {
      setVisible(false);
      const t = setTimeout(() => {
        prevPath.current = location.pathname;
        setVisible(true);
      }, 120);
      return () => clearTimeout(t);
    }
  }, [location.pathname]);

  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(6px)',
        transition: 'opacity 0.2s ease, transform 0.2s ease',
      }}
    >
      <Outlet />
    </div>
  );
}

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const { isDark, toggle: toggleTheme } = useTheme();
  const { token: themeToken } = theme.useToken();

  const { data: onlineStats } = useQuery({
    queryKey: ['online-order-stats'],
    queryFn: getOnlineOrderStats,
    refetchInterval: 15_000,
    enabled: isAdmin,
  });
  const pendingCount = onlineStats?.pendiente ?? 0;

  const menuItems = [
    ...(isAdmin
      ? [
          {
            key: '/',
            icon: <DashboardOutlined />,
            label: 'Dashboard',
          },
        ]
      : []),
    {
      key: isAdmin ? '/sales/list' : '/sales',
      icon: <ShoppingCartOutlined />,
      label: 'Ventas',
    },
    {
      key: '/products',
      icon: <AppstoreOutlined />,
      label: 'Productos',
    },
    ...(isAdmin
      ? [
          {
            key: '/inventory',
            icon: <InboxOutlined />,
            label: 'Inventario',
            children: [
              { key: '/inventory', label: 'Stock' },
              { key: '/inventory/movements', label: 'Movimientos' },
              { key: '/inventory/alerts', label: 'Alertas' },
              { key: '/inventory/stock-valorizado', label: 'Stock Valorizado' },
              { key: '/inventory/kardex', label: 'Kardex' },
            ],
          },
        ]
      : [
          {
            key: '/inventory/alerts',
            icon: <InboxOutlined />,
            label: 'Alertas Stock',
          },
        ]),
    {
      key: '/clients',
      icon: <TeamOutlined />,
      label: 'Clientes',
    },
    {
      key: '/online-orders',
      icon: <GlobalOutlined />,
      label: pendingCount > 0 ? (
        <span>Pedidos Online <Badge count={pendingCount} size="small" offset={[4, -2]} /></span>
      ) : 'Pedidos Online',
    },
    ...(isAdmin
      ? [
          {
            key: '/purchase-orders',
            icon: <ShoppingOutlined />,
            label: 'Compras',
            children: [
              { key: '/purchase-orders', label: 'Ordenes' },
              { key: '/purchase-orders/restock', label: 'Smart Restock' },
            ],
          },
          {
            key: '/cuentas-por-pagar',
            icon: <DollarOutlined />,
            label: 'Ctas por Pagar',
          },
          {
            key: '/sunat',
            icon: <CloudUploadOutlined />,
            label: 'Envio SUNAT',
          },
          {
            key: '/reports',
            icon: <BarChartOutlined />,
            label: 'Reportes',
          },
          {
            key: '/trabajadores',
            icon: <IdcardOutlined />,
            label: 'Trabajadores',
            children: [
              { key: '/trabajadores', label: 'Lista' },
              { key: '/trabajadores/asistencia', label: 'Asistencia' },
            ],
          },
          {
            key: '/users',
            icon: <UserOutlined />,
            label: 'Usuarios',
          },
          {
            key: '/chat-history',
            icon: <MessageOutlined />,
            label: 'Historial Chat',
          },
          {
            key: '/web-chat-logs',
            icon: <GlobalOutlined />,
            label: 'Chat Web',
          },
          {
            key: '/settings',
            icon: <SettingOutlined />,
            label: 'Configuracion',
          },
        ]
      : []),
  ];

  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/sales')) return isAdmin ? '/sales/list' : '/sales';
    if (path.startsWith('/products')) return '/products';
    if (path === '/inventory/movements') return '/inventory/movements';
    if (path === '/inventory/alerts') return '/inventory/alerts';
    if (path === '/inventory/stock-valorizado') return '/inventory/stock-valorizado';
    if (path === '/inventory/kardex') return '/inventory/kardex';
    if (path.startsWith('/inventory')) return '/inventory';
    if (path.startsWith('/clients')) return '/clients';
    if (path.startsWith('/online-orders')) return '/online-orders';
    if (path === '/purchase-orders/restock') return '/purchase-orders/restock';
    if (path.startsWith('/purchase-orders')) return '/purchase-orders';
    if (path.startsWith('/cuentas-por-pagar')) return '/cuentas-por-pagar';
    if (path.startsWith('/sunat')) return '/sunat';
    if (path === '/trabajadores/asistencia') return '/trabajadores/asistencia';
    if (path.startsWith('/trabajadores')) return '/trabajadores';
    if (path.startsWith('/users')) return '/users';
    if (path.startsWith('/chat-history')) return '/chat-history';
    if (path.startsWith('/web-chat-logs')) return '/web-chat-logs';
    if (path.startsWith('/settings')) return '/settings';
    if (path.startsWith('/reports')) return '/reports';
    return '/';
  };

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Cerrar Sesion',
      onClick: handleLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        breakpoint="lg"
        onBreakpoint={(broken) => setCollapsed(broken)}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          ...(!isDark
            ? { background: 'linear-gradient(180deg, #c62828 0%, #8e1a1a 30%, #1a3a8f 70%, #0f2266 100%)' }
            : { background: 'rgba(6, 8, 15, 0.8)' }),
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: collapsed ? '20px 8px 16px' : '20px 16px 16px',
            cursor: 'pointer',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            marginBottom: 8,
          }}
          onClick={() => navigate('/')}
        >
          <img
            src={isDark ? '/kti-logo-white.png' : '/kti-logo.png'}
            alt="KTI"
            style={{
              width: collapsed ? 38 : 85,
              objectFit: 'contain',
              transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 'none', background: 'transparent' }}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)' }}>
        <Header
          style={{
            padding: '0 24px',
            background: isDark ? 'rgba(6, 8, 15, 0.5)' : 'rgba(255, 255, 255, 0.7)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'}`,
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16 }}
          />
          <Space size={4}>
            <Button
              type="text"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              style={{ fontSize: 16 }}
            />
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Button type="text" icon={<UserOutlined />} style={{ fontWeight: 500 }}>
                {user?.full_name || user?.username}
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content
          style={{
            margin: '16px 20px 20px',
            padding: 24,
            background: isDark ? 'rgba(15, 23, 42, 0.4)' : themeToken.colorBgContainer,
            backdropFilter: isDark ? 'blur(16px)' : 'none',
            WebkitBackdropFilter: isDark ? 'blur(16px)' : 'none',
            borderRadius: 14,
            minHeight: 280,
            border: isDark ? '1px solid rgba(255,255,255,0.05)' : '1px solid rgba(0,0,0,0.04)',
          }}
        >
          <AnimatedOutlet />
        </Content>
      </Layout>
      <ChatWidget />
    </Layout>
  );
}
