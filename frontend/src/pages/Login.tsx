import { useState } from 'react';
import { Card, Form, Input, Button, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

const { Text } = Typography;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();
  const { isDark } = useTheme();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      navigate('/');
    } catch {
      message.error('Credenciales incorrectas');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: isDark
          ? 'linear-gradient(135deg, #060e1e 0%, #0a1a36 50%, #060e1e 100%)'
          : 'linear-gradient(135deg, #0a1e4a 0%, #1a3a8f 50%, #0a1e4a 100%)',
      }}
    >
      <Card
        style={{
          width: 400,
          boxShadow: isDark ? '0 8px 32px rgba(0,0,0,0.5)' : '0 8px 32px rgba(0,0,0,0.3)',
          borderRadius: 12,
          ...(isDark
            ? { border: '1px solid #1e3050', background: '#152038' }
            : { border: 'none' }),
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <img
            src={isDark ? '/kti-logo-white.png' : '/kti-logo.png'}
            alt="KTI"
            style={{
              height: 80,
              objectFit: 'contain',
              marginBottom: 16,
              ...(isDark ? {} : { borderRadius: 8 }),
            }}
          />
          <div style={{ marginBottom: 4 }}>
            <Text style={{ fontSize: 14, color: isDark ? '#8899bb' : '#666' }}>
              INVERSIONES KTI D & E E.I.R.L.
            </Text>
          </div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Sistema de Punto de Venta
          </Text>
        </div>
        <Form name="login" onFinish={onFinish} autoComplete="off" size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Ingrese su usuario' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Usuario" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Ingrese su contrasena' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Contrasena" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Ingresar
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            KTI POS v1.0
          </Text>
        </div>
      </Card>
    </div>
  );
}
