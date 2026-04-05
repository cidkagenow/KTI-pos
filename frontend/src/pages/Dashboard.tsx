import { Row, Col, Card, Statistic, Spin, Typography, Tag, Table } from 'antd';
import {
  ShoppingCartOutlined,
  DollarOutlined,
  CalendarOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '../api/reports';
import { getAsistencia } from '../api/trabajadores';
import { formatCurrency } from '../utils/format';
import { useTheme } from '../contexts/ThemeContext';
import dayjs from 'dayjs';

const { Title } = Typography;

const STATUS_ICONS: Record<string, React.ReactNode> = {
  PRESENTE: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  TARDANZA: <ClockCircleOutlined style={{ color: '#faad14' }} />,
  AUSENTE: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
};

const STATUS_COLORS: Record<string, string> = {
  PRESENTE: 'green',
  TARDANZA: 'orange',
  AUSENTE: 'red',
};

export default function Dashboard() {
  const { isDark } = useTheme();
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    refetchInterval: 30_000,
  });

  const todayStr = dayjs().format('YYYY-MM-DD');
  const { data: asistenciaHoy } = useQuery({
    queryKey: ['asistencia', todayStr],
    queryFn: () => getAsistencia(todayStr),
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  const lowStock = (data?.low_stock_count ?? 0) > 0;

  const statCards = [
    {
      title: 'Ventas Hoy',
      value: data?.today_sales ?? 0,
      icon: <ShoppingCartOutlined />,
      gradient: isDark
        ? 'linear-gradient(135deg, rgba(26, 58, 143, 0.3) 0%, rgba(26, 58, 143, 0.1) 100%)'
        : 'linear-gradient(135deg, #1a3a8f 0%, #2550b0 100%)',
      iconBg: isDark ? 'rgba(96, 165, 250, 0.12)' : 'rgba(255,255,255,0.2)',
      accent: isDark ? '#93bbfd' : '#fff',
      border: isDark ? 'rgba(96, 165, 250, 0.15)' : 'transparent',
      delay: 0,
    },
    {
      title: 'Total Hoy',
      value: data?.today_total ?? 0,
      icon: <DollarOutlined />,
      formatter: (val: number | string) => formatCurrency(Number(val)),
      gradient: isDark
        ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(34, 197, 94, 0.05) 100%)'
        : 'linear-gradient(135deg, #16a34a 0%, #22c55e 100%)',
      iconBg: isDark ? 'rgba(52, 211, 153, 0.12)' : 'rgba(255,255,255,0.2)',
      accent: isDark ? '#6ee7b7' : '#fff',
      border: isDark ? 'rgba(52, 211, 153, 0.15)' : 'transparent',
      delay: 1,
    },
    {
      title: 'Ventas del Mes',
      value: data?.month_sales ?? 0,
      icon: <CalendarOutlined />,
      gradient: isDark
        ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(168, 85, 247, 0.05) 100%)'
        : 'linear-gradient(135deg, #7e22ce 0%, #9333ea 100%)',
      iconBg: isDark ? 'rgba(192, 132, 252, 0.12)' : 'rgba(255,255,255,0.2)',
      accent: isDark ? '#d8b4fe' : '#fff',
      border: isDark ? 'rgba(192, 132, 252, 0.15)' : 'transparent',
      delay: 2,
    },
    {
      title: 'Stock Bajo',
      value: data?.low_stock_count ?? 0,
      icon: <WarningOutlined />,
      gradient: lowStock
        ? (isDark ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(239, 68, 68, 0.05) 100%)' : 'linear-gradient(135deg, #c62828 0%, #e53935 100%)')
        : (isDark ? 'linear-gradient(135deg, rgba(100, 116, 139, 0.15) 0%, rgba(100, 116, 139, 0.05) 100%)' : 'linear-gradient(135deg, #475569 0%, #64748b 100%)'),
      iconBg: lowStock
        ? (isDark ? 'rgba(248, 113, 113, 0.12)' : 'rgba(255,255,255,0.2)')
        : (isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(255,255,255,0.2)'),
      accent: isDark ? (lowStock ? '#fca5a5' : '#94a3b8') : '#fff',
      border: isDark ? (lowStock ? 'rgba(248, 113, 113, 0.15)' : 'rgba(148, 163, 184, 0.1)') : 'transparent',
      delay: 3,
    },
  ];

  return (
    <div>
      <style>{`
        @keyframes statCardIn {
          from { opacity: 0; transform: translateY(20px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <img src={isDark ? '/kti-logo-white.png' : '/kti-logo.png'} alt="KTI" style={{ height: 36, objectFit: 'contain', marginRight: 12 }} />
        <Title level={3} style={{ margin: 0, fontWeight: 600 }}>
          Panel de Control
        </Title>
      </Row>
      <Row gutter={[16, 16]}>
        {statCards.map((card) => (
          <Col xs={24} sm={12} lg={6} key={card.title}>
            <Card
              bordered={false}
              className="stat-card"
              style={{
                background: card.gradient,
                borderRadius: 14,
                border: `1px solid ${card.border}`,
                overflow: 'hidden',
                backdropFilter: isDark ? 'blur(16px)' : 'none',
                WebkitBackdropFilter: isDark ? 'blur(16px)' : 'none',
                animation: `statCardIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) ${card.delay * 0.12}s both`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Statistic
                  title={<span style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13, fontWeight: 500 }}>{card.title}</span>}
                  value={card.value}
                  formatter={card.formatter}
                  valueStyle={{ color: card.accent, fontSize: 30, fontWeight: 700 }}
                />
                <div
                  className="stat-icon"
                  style={{
                    fontSize: 24,
                    color: card.accent,
                    background: card.iconBg,
                    borderRadius: 12,
                    width: 48,
                    height: 48,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {card.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card
        title="Asistencia Hoy"
        bordered={false}
        style={{ marginTop: 24, borderRadius: 12 }}
        styles={{ header: { fontWeight: 600, borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'}` } }}
      >
        {(asistenciaHoy ?? []).length === 0 ? (
          <Typography.Text type="secondary">No se ha registrado asistencia hoy</Typography.Text>
        ) : (
          <Table
            dataSource={asistenciaHoy}
            rowKey="id"
            size="small"
            pagination={false}
            columns={[
              {
                title: 'Trabajador',
                dataIndex: 'trabajador_name',
                key: 'trabajador_name',
              },
              {
                title: 'Estado',
                dataIndex: 'status',
                key: 'status',
                width: 120,
                render: (status: string) => (
                  <Tag icon={STATUS_ICONS[status]} color={STATUS_COLORS[status] || 'default'}>
                    {status}
                  </Tag>
                ),
              },
              {
                title: 'Entrada',
                dataIndex: 'check_in_time',
                key: 'check_in_time',
                width: 80,
                render: (v: string | null) => v || '-',
              },
              {
                title: 'Salida',
                dataIndex: 'check_out_time',
                key: 'check_out_time',
                width: 80,
                render: (v: string | null) => v || '-',
              },
              {
                title: 'Notas',
                dataIndex: 'notes',
                key: 'notes',
                render: (v: string | null) => v || '-',
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}
