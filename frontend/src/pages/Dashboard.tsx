import { Row, Col, Card, Statistic, Spin, Typography } from 'antd';
import {
  ShoppingCartOutlined,
  DollarOutlined,
  CalendarOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '../api/reports';
import { formatCurrency } from '../utils/format';
import { useTheme } from '../contexts/ThemeContext';

const { Title } = Typography;

export default function Dashboard() {
  const { isDark } = useTheme();
  const accent = isDark ? '#5b8be6' : '#1a3a8f';
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
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
      <Title level={3} style={{ margin: '0 0 24px 0' }}>
        Panel de Control
      </Title>
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
    </div>
  );
}
