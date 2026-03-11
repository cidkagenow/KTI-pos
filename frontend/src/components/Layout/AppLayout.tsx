import { useState } from 'react';
import { Layout, Menu, Button, Dropdown, Space, theme } from 'antd';
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
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import ChatWidget from '../Chat/ChatWidget';

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const { isDark, toggle: toggleTheme } = useTheme();
  const { token: themeToken } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
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
            ],
          },
        ]
      : []),
    {
      key: '/clients',
      icon: <TeamOutlined />,
      label: 'Clientes',
    },
    ...(isAdmin
      ? [
          {
            key: '/purchase-orders',
            icon: <ShoppingOutlined />,
            label: 'Compras',
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
    if (path.startsWith('/inventory')) return '/inventory';
    if (path.startsWith('/clients')) return '/clients';
    if (path.startsWith('/purchase-orders')) return '/purchase-orders';
    if (path.startsWith('/sunat')) return '/sunat';
    if (path.startsWith('/users')) return '/users';
    if (path.startsWith('/chat-history')) return '/chat-history';
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
          ...(!isDark ? { background: 'linear-gradient(180deg, #b02a2a 0%, #1a3a8f 100%)' } : {}),
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: collapsed ? '20px 8px 24px' : '20px 16px 24px',
            cursor: 'pointer',
          }}
          onClick={() => navigate('/')}
        >
          <img
            src={isDark ? '/kti-logo-white.png' : '/kti-logo.png'}
            alt="KTI"
            style={{
              width: collapsed ? 40 : 90,
              objectFit: 'contain',
              transition: 'width 0.2s',
            }}
          />
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: themeToken.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Space>
            <Button
              type="text"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
            />
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Button type="text" icon={<UserOutlined />}>
                {user?.full_name || user?.username}
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: themeToken.colorBgContainer,
            borderRadius: themeToken.borderRadiusLG,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
      <ChatWidget />
    </Layout>
  );
}
