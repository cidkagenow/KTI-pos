import { useState } from 'react';
import { Card, Form, Input, Button, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import useEnterNavigation from '../hooks/useEnterNavigation';

const { Text } = Typography;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();
  const { isDark } = useTheme();
  const [form] = Form.useForm();
  const enterNavRef = useEnterNavigation(() => form.submit());

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
          ? 'linear-gradient(135deg, #060e1e 0%, #0c1a36 50%, #0a1230 100%)'
          : 'linear-gradient(135deg, #c62828 0%, #8e1a1a 35%, #1a3a8f 65%, #0f2266 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <style>{`
        @keyframes loginCardIn {
          from { opacity: 0; transform: translateY(30px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes loginLogoIn {
          from { opacity: 0; transform: scale(0.8); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes loginFormIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes glowPulse {
          0%, 100% { opacity: 0.4; transform: translate(-50%, -50%) scale(1); }
          50% { opacity: 0.6; transform: translate(-50%, -50%) scale(1.1); }
        }
      `}</style>
      {/* Animated background glow */}
      <div style={{
        position: 'absolute',
        width: 600,
        height: 600,
        borderRadius: '50%',
        background: isDark
          ? 'radial-gradient(circle, rgba(198, 40, 40, 0.08) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%)',
        top: '40%',
        left: '50%',
        animation: 'glowPulse 4s ease-in-out infinite',
        pointerEvents: 'none',
      }} />
      <Card
        style={{
          width: 400,
          boxShadow: '0 24px 80px rgba(0,0,0,0.4)',
          borderRadius: 20,
          animation: 'loginCardIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          ...(isDark
            ? { border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(15, 23, 42, 0.7)' }
            : { border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(255, 255, 255, 0.85)' }),
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
              animation: 'loginLogoIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.15s both',
              ...(isDark ? {} : { borderRadius: 8 }),
            }}
          />
          <div style={{ marginBottom: 4, animation: 'loginFormIn 0.4s ease-out 0.3s both' }}>
            <Text style={{ fontSize: 13, color: isDark ? 'rgba(255,255,255,0.45)' : '#666', letterSpacing: 1, fontWeight: 500 }}>
              INVERSIONES KTI D & E E.I.R.L.
            </Text>
          </div>
          <div style={{ animation: 'loginFormIn 0.4s ease-out 0.35s both' }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Sistema de Punto de Venta
            </Text>
          </div>
        </div>
        <div ref={enterNavRef} style={{ animation: 'loginFormIn 0.4s ease-out 0.4s both' }}>
        <Form form={form} name="login" onFinish={onFinish} autoComplete="off" size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Ingrese su usuario' }]}
          >
            <Input prefix={<UserOutlined style={{ color: isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.25)' }} />} placeholder="Usuario" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Ingrese su contrasena' }]}
          >
            <Input.Password prefix={<LockOutlined style={{ color: isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.25)' }} />} placeholder="Contrasena" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block style={{ height: 46, fontWeight: 600, borderRadius: 10, fontSize: 15 }}>
              Ingresar
            </Button>
          </Form.Item>
        </Form>
        </div>
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            KTI POS v1.0
          </Text>
        </div>
      </Card>
    </div>
  );
}
