import { useState } from 'react';
import {
  Typography,
  Tabs,
  Table,
  DatePicker,
  Select,
  InputNumber,
  Row,
  Col,
  Space,
  Button,
  Card,
  Tag,
} from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { ColumnsType } from 'antd/es/table';
import { getSalesByPeriod, getTopProducts, getProfitReport } from '../../api/reports';
import { formatCurrency } from '../../utils/format';
import type { SalesByPeriod, TopProduct, ProfitReport } from '../../types';

const { Title } = Typography;
const { RangePicker } = DatePicker;

/* ---------- helpers ---------- */

const startOfMonth = dayjs().startOf('month');
const today = dayjs();

function exportCSV(data: ProfitReport[], fromDate: string, toDate: string) {
  const headers = [
    'Codigo',
    'Articulo',
    'Marca',
    'Cant.Tot.Unid',
    'Importe Tot.Venta',
    'Costo Total',
    'Utilidad Total',
    'P.Rentabilidad (%)',
  ];

  const rows = data.map((r) => [
    r.product_code,
    `"${r.product_name.replace(/"/g, '""')}"`,
    r.brand_name ?? '',
    r.quantity_sold,
    r.total_revenue.toFixed(2),
    r.total_cost.toFixed(2),
    r.profit.toFixed(2),
    r.profit_margin.toFixed(2),
  ]);

  // Totals row
  const totQty = data.reduce((s, r) => s + r.quantity_sold, 0);
  const totRevenue = data.reduce((s, r) => s + r.total_revenue, 0);
  const totCost = data.reduce((s, r) => s + r.total_cost, 0);
  const totProfit = data.reduce((s, r) => s + r.profit, 0);
  const totMargin = totRevenue > 0 ? (totProfit / totRevenue) * 100 : 0;

  rows.push([
    '',
    '"TOTALES"',
    '',
    totQty as unknown as string,
    totRevenue.toFixed(2),
    totCost.toFixed(2),
    totProfit.toFixed(2),
    totMargin.toFixed(2),
  ] as unknown as string[]);

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `reporte_utilidades_${fromDate}_${toDate}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/* ---------- Ventas por Periodo ---------- */

function VentasPorPeriodo() {
  const [dates, setDates] = useState<[Dayjs, Dayjs]>([startOfMonth, today]);
  const [groupBy, setGroupBy] = useState<string>('day');

  const fromDate = dates[0].format('YYYY-MM-DD');
  const toDate = dates[1].format('YYYY-MM-DD');

  const { data, isLoading } = useQuery({
    queryKey: ['salesByPeriod', fromDate, toDate, groupBy],
    queryFn: () => getSalesByPeriod(fromDate, toDate, groupBy),
  });

  const columns: ColumnsType<SalesByPeriod> = [
    {
      title: 'Periodo',
      dataIndex: 'period',
      key: 'period',
    },
    {
      title: '# Ventas',
      dataIndex: 'count',
      key: 'count',
      align: 'right',
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      align: 'right',
      render: (val: number) => formatCurrency(val),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <Space>
            <span>Rango:</span>
            <RangePicker
              value={dates}
              onChange={(vals) => {
                if (vals && vals[0] && vals[1]) setDates([vals[0], vals[1]]);
              }}
              format="DD/MM/YYYY"
            />
          </Space>
        </Col>
        <Col>
          <Space>
            <span>Agrupar por:</span>
            <Select
              value={groupBy}
              onChange={setGroupBy}
              style={{ width: 120 }}
              options={[
                { value: 'day', label: 'Dia' },
                { value: 'week', label: 'Semana' },
                { value: 'month', label: 'Mes' },
              ]}
            />
          </Space>
        </Col>
      </Row>

      <Card style={{ marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={data ?? []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [formatCurrency(Number(value ?? 0)), 'Total']}
            />
            <Bar dataKey="total" fill="#1890ff" name="Total Ventas" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Table
        dataSource={data ?? []}
        columns={columns}
        loading={isLoading}
        rowKey="period"
        pagination={false}
        size="small"
        summary={(pageData) => {
          const totalCount = pageData.reduce((s, r) => s + r.count, 0);
          const totalAmount = pageData.reduce((s, r) => s + r.total, 0);
          return (
            <Table.Summary.Row style={{ fontWeight: 'bold' }}>
              <Table.Summary.Cell index={0}>Total</Table.Summary.Cell>
              <Table.Summary.Cell index={1} align="right">
                {totalCount}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={2} align="right">
                {formatCurrency(totalAmount)}
              </Table.Summary.Cell>
            </Table.Summary.Row>
          );
        }}
      />
    </div>
  );
}

/* ---------- Top Productos ---------- */

function TopProductos() {
  const [dates, setDates] = useState<[Dayjs, Dayjs]>([startOfMonth, today]);
  const [limit, setLimit] = useState<number>(10);

  const fromDate = dates[0].format('YYYY-MM-DD');
  const toDate = dates[1].format('YYYY-MM-DD');

  const { data, isLoading } = useQuery({
    queryKey: ['topProducts', fromDate, toDate, limit],
    queryFn: () => getTopProducts(fromDate, toDate, limit),
  });

  const columns: ColumnsType<TopProduct> = [
    {
      title: '#',
      key: 'index',
      width: 50,
      render: (_val, _rec, idx) => idx + 1,
    },
    {
      title: 'Producto',
      dataIndex: 'product_name',
      key: 'product_name',
    },
    {
      title: 'Cantidad Vendida',
      dataIndex: 'quantity_sold',
      key: 'quantity_sold',
      align: 'right',
    },
    {
      title: 'Ingresos',
      dataIndex: 'total_revenue',
      key: 'total_revenue',
      align: 'right',
      render: (val: number) => formatCurrency(val),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <Space>
            <span>Rango:</span>
            <RangePicker
              value={dates}
              onChange={(vals) => {
                if (vals && vals[0] && vals[1]) setDates([vals[0], vals[1]]);
              }}
              format="DD/MM/YYYY"
            />
          </Space>
        </Col>
        <Col>
          <Space>
            <span>Limite:</span>
            <InputNumber
              value={limit}
              min={1}
              max={100}
              onChange={(val) => setLimit(val ?? 10)}
              style={{ width: 80 }}
            />
          </Space>
        </Col>
      </Row>

      <Table
        dataSource={data ?? []}
        columns={columns}
        loading={isLoading}
        rowKey="product_name"
        pagination={false}
        size="small"
      />
    </div>
  );
}

/* ---------- Reporte de Utilidades ---------- */

function ReporteUtilidades() {
  const [dates, setDates] = useState<[Dayjs, Dayjs]>([startOfMonth, today]);

  const fromDate = dates[0].format('YYYY-MM-DD');
  const toDate = dates[1].format('YYYY-MM-DD');

  const { data, isLoading } = useQuery({
    queryKey: ['profitReport', fromDate, toDate],
    queryFn: () => getProfitReport(fromDate, toDate),
  });

  const columns: ColumnsType<ProfitReport> = [
    {
      title: 'Codigo',
      dataIndex: 'product_code',
      key: 'product_code',
      width: 100,
    },
    {
      title: 'Articulo',
      dataIndex: 'product_name',
      key: 'product_name',
      ellipsis: true,
    },
    {
      title: 'Marca',
      dataIndex: 'brand_name',
      key: 'brand_name',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: 'Cant.Tot.Unid',
      dataIndex: 'quantity_sold',
      key: 'quantity_sold',
      align: 'right',
      width: 110,
    },
    {
      title: 'Importe Tot.Venta',
      dataIndex: 'total_revenue',
      key: 'total_revenue',
      align: 'right',
      width: 140,
      render: (val: number) => formatCurrency(val),
    },
    {
      title: 'Costo Total',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right',
      width: 120,
      render: (val: number) => formatCurrency(val),
    },
    {
      title: 'Utilidad Total',
      dataIndex: 'profit',
      key: 'profit',
      align: 'right',
      width: 120,
      render: (val: number) => formatCurrency(val),
    },
    {
      title: 'P.Rentabilidad',
      dataIndex: 'profit_margin',
      key: 'profit_margin',
      align: 'center',
      width: 130,
      sorter: (a, b) => a.profit_margin - b.profit_margin,
      render: (val: number) => {
        let color = 'red';
        if (val >= 20) color = 'green';
        else if (val >= 10) color = 'gold';
        return <Tag color={color}>{val.toFixed(2)}%</Tag>;
      },
    },
  ];

  const totals = (data ?? []).reduce(
    (acc, r) => ({
      quantity_sold: acc.quantity_sold + r.quantity_sold,
      total_revenue: acc.total_revenue + r.total_revenue,
      total_cost: acc.total_cost + r.total_cost,
      profit: acc.profit + r.profit,
    }),
    { quantity_sold: 0, total_revenue: 0, total_cost: 0, profit: 0 },
  );
  const totalMargin =
    totals.total_revenue > 0
      ? (totals.profit / totals.total_revenue) * 100
      : 0;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }} align="middle" justify="space-between">
        <Col>
          <Space>
            <span>Rango:</span>
            <RangePicker
              value={dates}
              onChange={(vals) => {
                if (vals && vals[0] && vals[1]) setDates([vals[0], vals[1]]);
              }}
              format="DD/MM/YYYY"
            />
          </Space>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            disabled={!data || data.length === 0}
            onClick={() => data && exportCSV(data, fromDate, toDate)}
          >
            Exportar CSV
          </Button>
        </Col>
      </Row>

      <Table
        dataSource={data ?? []}
        columns={columns}
        loading={isLoading}
        rowKey="product_code"
        pagination={{ pageSize: 50, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
        size="small"
        scroll={{ x: 1000 }}
        summary={() => {
          if (!data || data.length === 0) return null;
          let marginColor = 'red';
          if (totalMargin >= 20) marginColor = 'green';
          else if (totalMargin >= 10) marginColor = 'gold';

          return (
            <Table.Summary fixed>
              <Table.Summary.Row style={{ fontWeight: 'bold', background: '#fafafa' }}>
                <Table.Summary.Cell index={0}>TOTALES</Table.Summary.Cell>
                <Table.Summary.Cell index={1} />
                <Table.Summary.Cell index={2} />
                <Table.Summary.Cell index={3} align="right">
                  {totals.quantity_sold}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  {formatCurrency(totals.total_revenue)}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  {formatCurrency(totals.total_cost)}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="right">
                  {formatCurrency(totals.profit)}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={7} align="center">
                  <Tag color={marginColor}>{totalMargin.toFixed(2)}%</Tag>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          );
        }}
      />
    </div>
  );
}

/* ---------- Main Reports Page ---------- */

export default function Reports() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        Reportes Gerenciales
      </Title>

      <Tabs
        defaultActiveKey="ventas"
        type="card"
        items={[
          {
            key: 'ventas',
            label: 'Ventas por Periodo',
            children: <VentasPorPeriodo />,
          },
          {
            key: 'top',
            label: 'Top Productos',
            children: <TopProductos />,
          },
          {
            key: 'utilidades',
            label: 'Reporte de Utilidades',
            children: <ReporteUtilidades />,
          },
        ]}
      />
    </div>
  );
}
