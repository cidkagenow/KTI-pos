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
import type { Asistencia } from '../types';
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
  const accent = isDark ? '#5b8be6' : '#1a3a8f';
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

  return (
    <div>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <img src={isDark ? '/kti-logo-white.png' : '/kti-logo.png'} alt="KTI" style={{ height: 40, objectFit: 'contain', marginRight: 12 }} />
        <Title level={3} style={{ margin: 0 }}>
          Panel de Control
        </Title>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderLeft: `4px solid ${accent}` }}>
            <Statistic
              title="Ventas Hoy"
              value={data?.today_sales ?? 0}
              prefix={<ShoppingCartOutlined style={{ color: accent }} />}
              valueStyle={{ color: accent }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderLeft: `4px solid ${accent}` }}>
            <Statistic
              title="Total Hoy"
              value={data?.today_total ?? 0}
              prefix={<DollarOutlined style={{ color: accent }} />}
              formatter={(val) => formatCurrency(Number(val))}
              valueStyle={{ color: accent }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderLeft: `4px solid ${accent}` }}>
            <Statistic
              title="Ventas del Mes"
              value={data?.month_sales ?? 0}
              prefix={<CalendarOutlined style={{ color: accent }} />}
              valueStyle={{ color: accent }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderLeft: (data?.low_stock_count ?? 0) > 0 ? '4px solid #e31e24' : `4px solid ${accent}` }}>
            <Statistic
              title="Stock Bajo"
              value={data?.low_stock_count ?? 0}
              prefix={<WarningOutlined style={{ color: (data?.low_stock_count ?? 0) > 0 ? '#e31e24' : accent }} />}
              valueStyle={
                (data?.low_stock_count ?? 0) > 0 ? { color: '#e31e24' } : { color: accent }
              }
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Asistencia Hoy"
        bordered={false}
        style={{ marginTop: 24 }}
        styles={{ header: { fontWeight: 600 } }}
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
