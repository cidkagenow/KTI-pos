import { useState } from 'react';
import { Table, Select, DatePicker, Typography, Row, Col, Descriptions } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getKardex } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import { getProducts } from '../../api/products';
import { tokenizedFilter, tokenizedFilterSort } from '../../utils/search';
import { useTheme } from '../../contexts/ThemeContext';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const MOVEMENT_TYPE_MAP: Record<string, string> = {
  SALE: 'VTA',
  PURCHASE: 'COM',
  ADJUSTMENT: 'AJU',
  TRANSFER: 'TRF',
  VOID_RETURN: 'DEV',
  NC_RETURN: 'NC',
  VOID_NC_REVERSE: 'ANC',
};

interface KardexEntry {
  date: string;
  movement_type: string;
  doc_type: string | null;
  doc_series: string | null;
  doc_number: string | null;
  entrada_qty: number;
  entrada_cost_unit: number;
  entrada_cost_total: number;
  salida_qty: number;
  salida_cost_unit: number;
  salida_cost_total: number;
  saldo_qty: number;
  saldo_cost_unit: number;
  saldo_cost_total: number;
}

interface KardexResponse {
  product_code: string;
  product_name: string;
  warehouse_name: string | null;
  initial_balance_qty: number;
  initial_balance_cost: number;
  entries: KardexEntry[];
}

const fmtQty = (v: number) => (v === 0 ? '' : v.toLocaleString('es-PE', { minimumFractionDigits: 0, maximumFractionDigits: 2 }));
const fmtCost = (v: number) => (v === 0 ? '' : v.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 4 }));
const fmtTotal = (v: number) => (v === 0 ? '' : v.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));

export default function Kardex() {
  const { isDark } = useTheme();
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [warehouseId, setWarehouseId] = useState<number | undefined>(1);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  const params: any = {};
  if (productId) params.product_id = productId;
  if (warehouseId) params.warehouse_id = warehouseId;
  if (dateRange) {
    params.date_from = dateRange[0].format('YYYY-MM-DD');
    params.date_to = dateRange[1].format('YYYY-MM-DD');
  }

  const { data: kardexData, isLoading } = useQuery<KardexResponse>({
    queryKey: ['kardex', params],
    queryFn: () => getKardex(params),
    enabled: !!productId,
  });

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: () => getProducts() });

  // Build table data: initial balance row + entries
  const tableData: (KardexEntry & { _key: string })[] = [];
  if (kardexData) {
    // Show initial balance row only when date filter is applied
    if (dateRange) {
      tableData.push({
        _key: 'initial',
        date: params.date_from || '',
        movement_type: 'SALDO_INICIAL',
        doc_type: null,
        doc_series: null,
        doc_number: null,
        entrada_qty: 0,
        entrada_cost_unit: 0,
        entrada_cost_total: 0,
        salida_qty: 0,
        salida_cost_unit: 0,
        salida_cost_total: 0,
        saldo_qty: kardexData.initial_balance_qty,
        saldo_cost_unit: kardexData.initial_balance_qty !== 0
          ? kardexData.initial_balance_cost / kardexData.initial_balance_qty
          : 0,
        saldo_cost_total: kardexData.initial_balance_cost,
      });
    }
    kardexData.entries.forEach((e, i) => {
      tableData.push({ ...e, _key: `entry-${i}` });
    });
  }

  const entradaBg = isDark ? 'rgba(56, 158, 13, 0.15)' : '#f6ffed';
  const salidaBg = isDark ? 'rgba(250, 173, 20, 0.15)' : '#fffbe6';

  const columns: ColumnsType<KardexEntry & { _key: string }> = [
    {
      title: 'Fecha',
      dataIndex: 'date',
      key: 'date',
      width: 100,
      fixed: 'left' as const,
    },
    {
      title: 'TipoDoc',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 70,
      render: (v: string | null) => v || '-',
    },
    {
      title: 'Serie',
      dataIndex: 'doc_series',
      key: 'doc_series',
      width: 70,
      render: (v: string | null) => v || '-',
    },
    {
      title: 'Numero',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 80,
      render: (v: string | null) => v || '-',
    },
    {
      title: 'TipoOp',
      dataIndex: 'movement_type',
      key: 'movement_type',
      width: 70,
      render: (v: string) => v === 'SALDO_INICIAL' ? 'S.INI' : (MOVEMENT_TYPE_MAP[v] || v),
    },
    {
      title: 'ENTRADAS',
      children: [
        {
          title: 'Cantidad',
          dataIndex: 'entrada_qty',
          key: 'entrada_qty',
          width: 80,
          align: 'right' as const,
          onCell: () => ({ style: { backgroundColor: entradaBg } }),
          render: fmtQty,
        },
        {
          title: 'C. Unit.',
          dataIndex: 'entrada_cost_unit',
          key: 'entrada_cost_unit',
          width: 90,
          align: 'right' as const,
          onCell: () => ({ style: { backgroundColor: entradaBg } }),
          render: fmtCost,
        },
        {
          title: 'C. Total',
          dataIndex: 'entrada_cost_total',
          key: 'entrada_cost_total',
          width: 100,
          align: 'right' as const,
          onCell: () => ({ style: { backgroundColor: entradaBg } }),
          render: fmtTotal,
        },
      ],
    },
    {
      title: 'SALIDAS',
      children: [
        {
          title: 'Cantidad',
          dataIndex: 'salida_qty',
          key: 'salida_qty',
          width: 80,
          align: 'right' as const,
          onCell: () => ({ style: { backgroundColor: salidaBg } }),
          render: fmtQty,
        },
        {
          title: 'C. Unit.',
          dataIndex: 'salida_cost_unit',
          key: 'salida_cost_unit',
          width: 90,
          align: 'right' as const,
          onCell: () => ({ style: { backgroundColor: salidaBg } }),
          render: fmtCost,
        },
        {
          title: 'C. Total',
          dataIndex: 'salida_cost_total',
          key: 'salida_cost_total',
          width: 100,
          align: 'right' as const,
          onCell: () => ({ style: { backgroundColor: salidaBg } }),
          render: fmtTotal,
        },
      ],
    },
    {
      title: 'SALDO FINAL',
      children: [
        {
          title: 'Cantidad',
          dataIndex: 'saldo_qty',
          key: 'saldo_qty',
          width: 80,
          align: 'right' as const,
          render: (v: number) => v.toLocaleString('es-PE', { minimumFractionDigits: 0, maximumFractionDigits: 2 }),
        },
        {
          title: 'C. Unit.',
          dataIndex: 'saldo_cost_unit',
          key: 'saldo_cost_unit',
          width: 90,
          align: 'right' as const,
          render: (v: number) => v.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 4 }),
        },
        {
          title: 'C. Total',
          dataIndex: 'saldo_cost_total',
          key: 'saldo_cost_total',
          width: 100,
          align: 'right' as const,
          render: (v: number) => v.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        },
      ],
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>Kardex</Title>

      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col>
          <Select
            placeholder="Producto (requerido)"
            style={{ width: 300 }}
            showSearch
            filterOption={tokenizedFilter}
            filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
            popupMatchSelectWidth={500}
            onChange={(val) => setProductId(val)}
            options={products?.map((p) => ({ value: p.id, label: `${p.code} - ${p.name}` }))}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="Almacen"
            style={{ width: 180 }}
            onChange={(val) => setWarehouseId(val)}
            options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
          />
        </Col>
        <Col>
          <RangePicker
            onChange={(dates) =>
              setDateRange(dates ? [dates[0]!, dates[1]!] : null)
            }
          />
        </Col>
      </Row>

      {kardexData && (
        <Descriptions
          size="small"
          bordered
          column={3}
          style={{ marginBottom: 16 }}
        >
          <Descriptions.Item label="Codigo">{kardexData.product_code}</Descriptions.Item>
          <Descriptions.Item label="Producto">{kardexData.product_name}</Descriptions.Item>
          <Descriptions.Item label="Almacen">{kardexData.warehouse_name || 'Todos'}</Descriptions.Item>
        </Descriptions>
      )}

      <Table
        columns={columns}
        dataSource={tableData}
        rowKey="_key"
        loading={isLoading && !!productId}
        size="small"
        pagination={false}
        scroll={{ x: 1200, y: 600 }}
        bordered
      />
    </div>
  );
}
