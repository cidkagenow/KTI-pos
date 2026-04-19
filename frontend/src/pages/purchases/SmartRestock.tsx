import { useState } from 'react';
import { Typography, Select, Card, Table, Tag, Space, Empty, Spin, Row, Col, Statistic, Tooltip, Tabs, InputNumber } from 'antd';
import { PhoneOutlined, MailOutlined, EnvironmentOutlined, ShoppingCartOutlined, RiseOutlined, FallOutlined, StopOutlined, ArrowUpOutlined, ArrowDownOutlined, DollarOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { getRestockSuggestions, getDemandAnalysis, getPriceOptimization, getFxImpact } from '../../api/purchases';
import { getWarehouses } from '../../api/catalogs';
import { formatCurrency } from '../../utils/format';
import { tokenizedFilter, tokenizedFilterSort } from '../../utils/search';
import SearchInput from '../../components/SearchInput';
import useFuzzyFilter from '../../hooks/useFuzzyFilter';

const { Title, Text } = Typography;

interface RestockItem {
  product_id: number;
  product_code: string;
  product_name: string;
  brand_name: string | null;
  current_stock: number;
  min_stock: number;
  suggested_qty: number;
  daily_sales: number;
  days_until_empty: number | null;
  urgency: 'critical' | 'low' | 'upcoming';
  last_cost: number;
  estimated_total: number;
}

interface SupplierGroup {
  supplier_id: number | null;
  business_name: string;
  ruc: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  items: RestockItem[];
  total_estimated_cost: number;
  total_items: number;
}

const urgencyConfig = {
  critical: { color: 'red', label: 'Sin stock' },
  low: { color: 'orange', label: 'Bajo' },
  upcoming: { color: 'blue', label: 'Por agotarse' },
};

const columns = [
  {
    title: 'Estado',
    dataIndex: 'urgency',
    key: 'urgency',
    width: 100,
    render: (v: keyof typeof urgencyConfig) => {
      const cfg = urgencyConfig[v];
      return <Tag color={cfg.color}>{cfg.label}</Tag>;
    },
  },
  {
    title: 'Codigo',
    dataIndex: 'product_code',
    key: 'product_code',
    width: 80,
  },
  {
    title: 'Producto',
    dataIndex: 'product_name',
    key: 'product_name',
    ellipsis: true,
  },
  {
    title: 'Marca',
    dataIndex: 'brand_name',
    key: 'brand_name',
    width: 100,
    render: (v: string | null) => v || '-',
  },
  {
    title: 'Stock',
    dataIndex: 'current_stock',
    key: 'current_stock',
    width: 70,
    align: 'right' as const,
    render: (v: number) => (
      <span style={{ color: v <= 0 ? '#f87171' : '#fbbf24', fontWeight: 600 }}>{v}</span>
    ),
  },
  {
    title: 'Dias restantes',
    dataIndex: 'days_until_empty',
    key: 'days_until_empty',
    width: 110,
    align: 'right' as const,
    render: (v: number | null) => {
      if (v === null) return '-';
      if (v <= 0) return <span style={{ color: '#f87171', fontWeight: 600 }}>0</span>;
      return <span style={{ color: v <= 7 ? '#fbbf24' : undefined }}>{v}d</span>;
    },
  },
  {
    title: 'Ventas/dia',
    dataIndex: 'daily_sales',
    key: 'daily_sales',
    width: 90,
    align: 'right' as const,
    render: (v: number) => v > 0 ? v.toFixed(1) : '-',
  },
  {
    title: 'Sugerido',
    dataIndex: 'suggested_qty',
    key: 'suggested_qty',
    width: 90,
    align: 'right' as const,
    render: (v: number) => <Tag color="blue">{v}</Tag>,
  },
  {
    title: 'Costo Unit',
    dataIndex: 'last_cost',
    key: 'last_cost',
    width: 100,
    align: 'right' as const,
    render: (v: number) => v > 0 ? formatCurrency(v) : '-',
  },
  {
    title: 'Total Est.',
    dataIndex: 'estimated_total',
    key: 'estimated_total',
    width: 110,
    align: 'right' as const,
    render: (v: number) => <strong>{formatCurrency(v)}</strong>,
  },
];

const demandConfig = {
  high_demand: { color: 'green', label: 'Alta demanda', icon: <ArrowUpOutlined /> },
  normal: { color: 'blue', label: 'Normal', icon: null },
  slow_moving: { color: 'orange', label: 'Lento', icon: <ArrowDownOutlined /> },
  dead_stock: { color: 'red', label: 'Sin movimiento', icon: <StopOutlined /> },
};

const recommendConfig = {
  buy_more: { color: 'green', label: 'Comprar mas' },
  maintain: { color: 'blue', label: 'Mantener' },
  buy_less: { color: 'orange', label: 'Comprar menos' },
  stop_buying: { color: 'red', label: 'No comprar' },
};

const demandColumns = [
  {
    title: 'Demanda',
    dataIndex: 'demand',
    key: 'demand',
    width: 130,
    render: (v: string) => {
      const cfg = demandConfig[v as keyof typeof demandConfig];
      return cfg ? <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag> : v;
    },
  },
  {
    title: 'Accion',
    dataIndex: 'recommendation',
    key: 'recommendation',
    width: 130,
    render: (v: string) => {
      const cfg = recommendConfig[v as keyof typeof recommendConfig];
      return cfg ? <Tag color={cfg.color}>{cfg.label}</Tag> : v;
    },
  },
  { title: 'Codigo', dataIndex: 'product_code', key: 'product_code', width: 80 },
  { title: 'Producto', dataIndex: 'product_name', key: 'product_name', ellipsis: true },
  { title: 'Marca', dataIndex: 'brand_name', key: 'brand_name', width: 100, render: (v: string | null) => v || '-' },
  {
    title: 'Stock',
    dataIndex: 'total_stock',
    key: 'total_stock',
    width: 70,
    align: 'right' as const,
    render: (v: number) => <span style={{ fontWeight: 600, color: v <= 0 ? '#f87171' : undefined }}>{v}</span>,
  },
  {
    title: 'Vendido (90d)',
    dataIndex: 'total_sold',
    key: 'total_sold',
    width: 100,
    align: 'right' as const,
  },
  {
    title: 'Ventas/dia',
    dataIndex: 'daily_sales',
    key: 'daily_sales',
    width: 90,
    align: 'right' as const,
    render: (v: number) => v > 0 ? v.toFixed(1) : '-',
  },
  {
    title: 'Dias stock',
    dataIndex: 'days_of_stock',
    key: 'days_of_stock',
    width: 90,
    align: 'right' as const,
    render: (v: number | null) => {
      if (v === null) return <span style={{ opacity: 0.3 }}>sin ventas</span>;
      if (v <= 0) return <span style={{ color: '#f87171', fontWeight: 600 }}>0</span>;
      return <span style={{ color: v <= 14 ? '#fbbf24' : undefined }}>{v}d</span>;
    },
  },
  {
    title: 'Ingresos',
    dataIndex: 'total_revenue',
    key: 'total_revenue',
    width: 110,
    align: 'right' as const,
    render: (v: number) => v > 0 ? formatCurrency(v) : '-',
  },
  {
    title: 'Capital en stock',
    dataIndex: 'stock_value',
    key: 'stock_value',
    width: 120,
    align: 'right' as const,
    render: (v: number) => v > 0 ? formatCurrency(v) : '-',
  },
];

export default function SmartRestock() {
  const [warehouseId, setWarehouseId] = useState<number | undefined>(1);
  const [demandSearch, setDemandSearch] = useState('');
  const [demandFilter, setDemandFilter] = useState<string | undefined>(undefined);
  const [priceSearch, setPriceSearch] = useState('');
  const [priceFilter, setPriceFilter] = useState<string | undefined>(undefined);
  const [fxRate, setFxRate] = useState(3.75);

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses'],
    queryFn: getWarehouses,
  });

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['restock-suggestions', warehouseId],
    queryFn: () => getRestockSuggestions(warehouseId),
    refetchInterval: 60_000,
  });

  const { data: allDemandData, isLoading: demandLoading } = useQuery({
    queryKey: ['demand-analysis', warehouseId],
    queryFn: () => getDemandAnalysis(warehouseId),
    refetchInterval: 60_000,
  });

  const { data: allPriceData, isLoading: priceLoading } = useQuery({
    queryKey: ['price-optimization', warehouseId],
    queryFn: () => getPriceOptimization(warehouseId),
    refetchInterval: 60_000,
  });

  const { data: fxData, isLoading: fxLoading } = useQuery({
    queryKey: ['fx-impact', fxRate],
    queryFn: () => getFxImpact(fxRate),
    refetchInterval: 60_000,
  });

  const filteredDemand = useFuzzyFilter(
    (allDemandData ?? []).filter((d: any) => !demandFilter || d.recommendation === demandFilter),
    demandSearch,
    (d: any) => `${d.product_code} ${d.product_name} ${d.brand_name || ''}`
  );

  const totalItems = suggestions?.reduce((sum: number, sg: SupplierGroup) => sum + sg.total_items, 0) ?? 0;
  const totalCost = suggestions?.reduce((sum: number, sg: SupplierGroup) => sum + sg.total_estimated_cost, 0) ?? 0;
  const totalSuppliers = suggestions?.filter((sg: SupplierGroup) => sg.supplier_id !== null).length ?? 0;

  const filteredPrice = useFuzzyFilter(
    (allPriceData ?? []).filter((d: any) => !priceFilter || d.price_action === priceFilter),
    priceSearch,
    (d: any) => `${d.product_code} ${d.product_name} ${d.brand_name || ''}`
  );

  const priceCounts = {
    raise_price: allPriceData?.filter((d: any) => d.price_action === 'raise_price').length ?? 0,
    lower_price: allPriceData?.filter((d: any) => d.price_action === 'lower_price').length ?? 0,
    discount: allPriceData?.filter((d: any) => d.price_action === 'discount').length ?? 0,
    keep: allPriceData?.filter((d: any) => d.price_action === 'keep').length ?? 0,
    review: allPriceData?.filter((d: any) => d.price_action === 'review').length ?? 0,
  };

  // Demand summary counts
  const demandCounts = {
    buy_more: allDemandData?.filter((d: any) => d.recommendation === 'buy_more').length ?? 0,
    maintain: allDemandData?.filter((d: any) => d.recommendation === 'maintain').length ?? 0,
    buy_less: allDemandData?.filter((d: any) => d.recommendation === 'buy_less').length ?? 0,
    stop_buying: allDemandData?.filter((d: any) => d.recommendation === 'stop_buying').length ?? 0,
  };

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ShoppingCartOutlined style={{ marginRight: 8 }} />
            Smart Restock
          </Title>
        </Col>
        <Col>
          <Select
            placeholder="Almacen"
            allowClear
            showSearch
            filterOption={tokenizedFilter}
            filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
            style={{ width: 200 }}
            value={warehouseId}
            onChange={(val) => setWarehouseId(val)}
            options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
          />
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="restock"
        items={[
          {
            key: 'restock',
            label: `Restock (${totalItems})`,
            children: (
              <>
                <Row gutter={16} style={{ marginBottom: 20 }}>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic title="Productos por reponer" value={totalItems} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic title="Proveedores" value={totalSuppliers} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic title="Costo total estimado" value={totalCost} prefix="S/" precision={2} />
                    </Card>
                  </Col>
                </Row>

                {isLoading ? (
                  <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
                ) : !suggestions || suggestions.length === 0 ? (
                  <Empty description="Todo el stock esta por encima del minimo" />
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {suggestions.map((sg: SupplierGroup, idx: number) => (
                      <Card
                        key={sg.supplier_id ?? `no-supplier-${idx}`}
                        size="small"
                        title={
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Space>
                              <Text strong style={{ fontSize: 15 }}>{sg.business_name}</Text>
                              {sg.ruc && <Tag>{sg.ruc}</Tag>}
                            </Space>
                            <Text strong style={{ fontSize: 14 }}>
                              {sg.total_items} productos — {formatCurrency(sg.total_estimated_cost)}
                            </Text>
                          </div>
                        }
                      >
                        {(sg.phone || sg.email || sg.address) && (
                          <div style={{ marginBottom: 12, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                            {sg.phone && (
                              <Tooltip title="Llamar">
                                <a href={`tel:${sg.phone}`} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                  <PhoneOutlined /> {sg.phone}
                                </a>
                              </Tooltip>
                            )}
                            {sg.email && (
                              <Tooltip title="Email">
                                <a href={`mailto:${sg.email}`} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                  <MailOutlined /> {sg.email}
                                </a>
                              </Tooltip>
                            )}
                            {(sg.address || sg.city) && (
                              <span style={{ display: 'flex', alignItems: 'center', gap: 4, opacity: 0.6 }}>
                                <EnvironmentOutlined /> {[sg.address, sg.city].filter(Boolean).join(', ')}
                              </span>
                            )}
                          </div>
                        )}
                        <Table columns={columns} dataSource={sg.items} rowKey="product_id" size="small" pagination={false} />
                      </Card>
                    ))}
                  </div>
                )}
              </>
            ),
          },
          {
            key: 'demand',
            label: 'Analisis de Demanda',
            children: (
              <>
                <Row gutter={16} style={{ marginBottom: 20 }}>
                  <Col span={6}>
                    <Card size="small" hoverable onClick={() => setDemandFilter(demandFilter === 'buy_more' ? undefined : 'buy_more')}>
                      <Statistic title="Comprar mas" value={demandCounts.buy_more} valueStyle={{ color: '#34d399' }} prefix={<ArrowUpOutlined />} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small" hoverable onClick={() => setDemandFilter(demandFilter === 'maintain' ? undefined : 'maintain')}>
                      <Statistic title="Mantener" value={demandCounts.maintain} valueStyle={{ color: '#60a5fa' }} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small" hoverable onClick={() => setDemandFilter(demandFilter === 'buy_less' ? undefined : 'buy_less')}>
                      <Statistic title="Comprar menos" value={demandCounts.buy_less} valueStyle={{ color: '#fbbf24' }} prefix={<ArrowDownOutlined />} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small" hoverable onClick={() => setDemandFilter(demandFilter === 'stop_buying' ? undefined : 'stop_buying')}>
                      <Statistic title="No comprar" value={demandCounts.stop_buying} valueStyle={{ color: '#f87171' }} prefix={<StopOutlined />} />
                    </Card>
                  </Col>
                </Row>

                <div style={{ marginBottom: 12 }}>
                  <SearchInput
                    value={demandSearch}
                    onChange={setDemandSearch}
                    placeholder="Buscar producto..."
                    style={{ width: 300 }}
                  />
                  {demandFilter && (
                    <Tag
                      closable
                      onClose={() => setDemandFilter(undefined)}
                      color={recommendConfig[demandFilter as keyof typeof recommendConfig]?.color}
                      style={{ marginLeft: 8 }}
                    >
                      {recommendConfig[demandFilter as keyof typeof recommendConfig]?.label}
                    </Tag>
                  )}
                </div>

                {demandLoading ? (
                  <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
                ) : (
                  <Table
                    columns={demandColumns}
                    dataSource={filteredDemand}
                    rowKey="product_id"
                    size="small"
                    pagination={{ pageSize: 20, showSizeChanger: true }}
                    scroll={{ x: 1200 }}
                  />
                )}
              </>
            ),
          },
          {
            key: 'price',
            label: 'Optimizar Precios',
            children: (
              <>
                <Row gutter={16} style={{ marginBottom: 20 }}>
                  <Col span={5}>
                    <Card size="small" hoverable onClick={() => setPriceFilter(priceFilter === 'raise_price' ? undefined : 'raise_price')}>
                      <Statistic title="Subir precio" value={priceCounts.raise_price} valueStyle={{ color: '#34d399' }} prefix={<ArrowUpOutlined />} />
                    </Card>
                  </Col>
                  <Col span={5}>
                    <Card size="small" hoverable onClick={() => setPriceFilter(priceFilter === 'lower_price' ? undefined : 'lower_price')}>
                      <Statistic title="Bajar precio" value={priceCounts.lower_price} valueStyle={{ color: '#fbbf24' }} prefix={<ArrowDownOutlined />} />
                    </Card>
                  </Col>
                  <Col span={5}>
                    <Card size="small" hoverable onClick={() => setPriceFilter(priceFilter === 'discount' ? undefined : 'discount')}>
                      <Statistic title="Descuento" value={priceCounts.discount} valueStyle={{ color: '#f87171' }} prefix={<FallOutlined />} />
                    </Card>
                  </Col>
                  <Col span={5}>
                    <Card size="small" hoverable onClick={() => setPriceFilter(priceFilter === 'keep' ? undefined : 'keep')}>
                      <Statistic title="Precio OK" value={priceCounts.keep} valueStyle={{ color: '#60a5fa' }} />
                    </Card>
                  </Col>
                  <Col span={4}>
                    <Card size="small" hoverable onClick={() => setPriceFilter(priceFilter === 'review' ? undefined : 'review')}>
                      <Statistic title="Revisar" value={priceCounts.review} valueStyle={{ color: '#a78bfa' }} />
                    </Card>
                  </Col>
                </Row>

                <div style={{ marginBottom: 12 }}>
                  <SearchInput
                    value={priceSearch}
                    onChange={setPriceSearch}
                    placeholder="Buscar producto..."
                    style={{ width: 300 }}
                  />
                  {priceFilter && (
                    <Tag
                      closable
                      onClose={() => setPriceFilter(undefined)}
                      style={{ marginLeft: 8 }}
                    >
                      {priceFilter === 'raise_price' ? 'Subir precio' :
                       priceFilter === 'lower_price' ? 'Bajar precio' :
                       priceFilter === 'discount' ? 'Descuento' :
                       priceFilter === 'keep' ? 'Precio OK' : 'Revisar'}
                    </Tag>
                  )}
                </div>

                {priceLoading ? (
                  <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
                ) : (
                  <Table
                    columns={[
                      {
                        title: 'Accion',
                        dataIndex: 'price_action',
                        key: 'price_action',
                        width: 120,
                        render: (v: string) => {
                          const cfg: Record<string, { color: string; label: string }> = {
                            raise_price: { color: 'green', label: 'Subir' },
                            lower_price: { color: 'orange', label: 'Bajar' },
                            discount: { color: 'red', label: 'Descuento' },
                            keep: { color: 'blue', label: 'OK' },
                            review: { color: 'purple', label: 'Revisar' },
                          };
                          const c = cfg[v];
                          return c ? <Tag color={c.color}>{c.label}</Tag> : v;
                        },
                      },
                      { title: 'Codigo', dataIndex: 'product_code', key: 'product_code', width: 80 },
                      { title: 'Producto', dataIndex: 'product_name', key: 'product_name', ellipsis: true },
                      { title: 'Marca', dataIndex: 'brand_name', key: 'brand_name', width: 100, render: (v: string | null) => v || '-' },
                      {
                        title: 'Costo',
                        dataIndex: 'cost_price',
                        key: 'cost_price',
                        width: 90,
                        align: 'right' as const,
                        render: (v: number) => formatCurrency(v),
                      },
                      {
                        title: 'Precio',
                        dataIndex: 'unit_price',
                        key: 'unit_price',
                        width: 90,
                        align: 'right' as const,
                        render: (v: number) => formatCurrency(v),
                      },
                      {
                        title: 'Margen',
                        dataIndex: 'margin_pct',
                        key: 'margin_pct',
                        width: 80,
                        align: 'right' as const,
                        render: (v: number) => (
                          <span style={{ color: v < 15 ? '#f87171' : v > 50 ? '#fbbf24' : '#34d399', fontWeight: 600 }}>
                            {v.toFixed(0)}%
                          </span>
                        ),
                      },
                      {
                        title: 'Ventas/dia',
                        dataIndex: 'daily_sales',
                        key: 'daily_sales',
                        width: 90,
                        align: 'right' as const,
                        render: (v: number) => v > 0 ? v.toFixed(1) : '-',
                      },
                      {
                        title: 'Vendido (90d)',
                        dataIndex: 'total_sold',
                        key: 'total_sold',
                        width: 100,
                        align: 'right' as const,
                      },
                      {
                        title: 'Razon',
                        dataIndex: 'reason',
                        key: 'reason',
                        ellipsis: true,
                        render: (v: string) => <span style={{ opacity: 0.7, fontSize: 12 }}>{v}</span>,
                      },
                    ]}
                    dataSource={filteredPrice}
                    rowKey="product_id"
                    size="small"
                    pagination={{ pageSize: 20, showSizeChanger: true }}
                    scroll={{ x: 1200 }}
                  />
                )}
              </>
            ),
          },
          {
            key: 'fx',
            label: 'Impacto FX',
            children: (
              <>
                <Row gutter={16} style={{ marginBottom: 20 }}>
                  <Col span={4}>
                    <Card size="small">
                      <div style={{ marginBottom: 4, fontSize: 12, opacity: 0.6 }}>Tipo de cambio hoy</div>
                      <InputNumber
                        value={fxRate}
                        onChange={(v) => v && setFxRate(v)}
                        min={0.01}
                        step={0.01}
                        precision={4}
                        prefix={<DollarOutlined />}
                        style={{ width: '100%' }}
                      />
                    </Card>
                  </Col>
                  {fxData?.summary && (
                    <>
                      <Col span={5}>
                        <Card size="small">
                          <Statistic title="Compras en USD" value={fxData.summary.total_orders} />
                        </Card>
                      </Col>
                      <Col span={5}>
                        <Card size="small">
                          <Statistic title="TC promedio pagado" value={fxData.summary.avg_rate_paid} precision={4} />
                        </Card>
                      </Col>
                      <Col span={5}>
                        <Card size="small">
                          <Statistic title="Total pagado" value={fxData.summary.total_paid_soles} prefix="S/" precision={2} />
                        </Card>
                      </Col>
                      <Col span={5}>
                        <Card size="small">
                          <Statistic
                            title="Impacto FX total"
                            value={Math.abs(fxData.summary.total_fx_impact)}
                            prefix={fxData.summary.total_fx_impact > 0 ? 'S/ +' : 'S/ -'}
                            precision={2}
                            valueStyle={{ color: fxData.summary.total_fx_impact > 0 ? '#f87171' : '#34d399' }}
                          />
                        </Card>
                      </Col>
                    </>
                  )}
                </Row>

                {fxData?.summary && (
                  <div
                    className={`px-4 py-3 rounded-lg border text-sm mb-4 ${
                      fxData.summary.total_fx_impact > 0
                        ? 'bg-red-500/10 border-red-500/20 text-red-300'
                        : 'bg-green-500/10 border-green-500/20 text-green-300'
                    }`}
                    style={{ background: fxData.summary.total_fx_impact > 0 ? 'rgba(248,113,113,0.1)' : 'rgba(52,211,153,0.1)', borderColor: fxData.summary.total_fx_impact > 0 ? 'rgba(248,113,113,0.2)' : 'rgba(52,211,153,0.2)', color: fxData.summary.total_fx_impact > 0 ? '#f87171' : '#34d399', padding: '12px 16px', borderRadius: 8, border: '1px solid', marginBottom: 16 }}
                  >
                    {fxData.summary.total_fx_impact > 0
                      ? `Pagaste S/ ${fxData.summary.total_fx_impact.toFixed(2)} de mas comprando a TC promedio de ${fxData.summary.avg_rate_paid.toFixed(4)} cuando hoy esta a ${fxRate}`
                      : `Ahorraste S/ ${Math.abs(fxData.summary.total_fx_impact).toFixed(2)} comprando a TC promedio de ${fxData.summary.avg_rate_paid.toFixed(4)} cuando hoy esta a ${fxRate}`
                    }
                  </div>
                )}

                {fxLoading ? (
                  <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
                ) : !fxData?.orders?.length ? (
                  <Empty description="No hay compras en dolares" />
                ) : (
                  <Table
                    columns={[
                      { title: 'Fecha', dataIndex: 'date', key: 'date', width: 100 },
                      { title: 'Doc', dataIndex: 'doc_number', key: 'doc_number', width: 100 },
                      { title: 'Proveedor', dataIndex: 'supplier_name', key: 'supplier_name', ellipsis: true },
                      {
                        title: 'USD',
                        dataIndex: 'usd_amount',
                        key: 'usd_amount',
                        width: 100,
                        align: 'right' as const,
                        render: (v: number) => `$ ${v.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`,
                      },
                      {
                        title: 'TC compra',
                        dataIndex: 'rate_at_purchase',
                        key: 'rate_at_purchase',
                        width: 90,
                        align: 'right' as const,
                        render: (v: number) => v.toFixed(4),
                      },
                      {
                        title: 'Pagado (S/)',
                        dataIndex: 'paid_soles',
                        key: 'paid_soles',
                        width: 110,
                        align: 'right' as const,
                        render: (v: number) => formatCurrency(v),
                      },
                      {
                        title: `A TC ${fxRate}`,
                        dataIndex: 'cost_at_current_rate',
                        key: 'cost_at_current_rate',
                        width: 110,
                        align: 'right' as const,
                        render: (v: number) => formatCurrency(v),
                      },
                      {
                        title: 'Impacto',
                        dataIndex: 'fx_impact',
                        key: 'fx_impact',
                        width: 110,
                        align: 'right' as const,
                        render: (v: number) => (
                          <span style={{ color: v > 0 ? '#f87171' : '#34d399', fontWeight: 600 }}>
                            {v > 0 ? '+' : ''}{formatCurrency(v)}
                          </span>
                        ),
                      },
                    ]}
                    dataSource={fxData.orders}
                    rowKey="po_id"
                    size="small"
                    pagination={{ pageSize: 20, showSizeChanger: true }}
                    scroll={{ x: 900 }}
                  />
                )}
              </>
            ),
          },
        ]}
      />
    </div>
  );
}
