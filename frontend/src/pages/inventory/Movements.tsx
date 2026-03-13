import { useState } from 'react';
import { Table, Select, Typography, Row, Col } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getMovements } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import { getProducts } from '../../api/products';
import { formatDateTime } from '../../utils/format';
import { tokenizedFilter, tokenizedFilterSort } from '../../utils/search';
import type { InventoryMovement } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const MOVEMENT_TYPES = [
  { value: 'SALE', label: 'Venta' },
  { value: 'PURCHASE', label: 'Compra' },
  { value: 'ADJUSTMENT', label: 'Ajuste' },
  { value: 'TRANSFER_IN', label: 'Transferencia entrada' },
  { value: 'TRANSFER_OUT', label: 'Transferencia salida' },
];

export default function Movements() {
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [productId, setProductId] = useState<number | undefined>(undefined);
  const [movementType, setMovementType] = useState<string | undefined>(undefined);

  const params: any = {};
  if (warehouseId) params.warehouse_id = warehouseId;
  if (productId) params.product_id = productId;
  if (movementType) params.movement_type = movementType;

  const { data: movements, isLoading } = useQuery({
    queryKey: ['movements', params],
    queryFn: () => getMovements(params),
    refetchInterval: 30_000,
  });

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: () => getProducts() });

  const columns: ColumnsType<InventoryMovement> = [
    {
      title: 'Fecha',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (val: string) => formatDateTime(val),
    },
    { title: 'Producto', dataIndex: 'product_name', key: 'product_name', ellipsis: true },
    { title: 'Almacen', dataIndex: 'warehouse_name', key: 'warehouse_name', width: 150 },
    { title: 'Tipo', dataIndex: 'movement_type', key: 'movement_type', width: 130 },
    {
      title: 'Cantidad',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      align: 'right',
      render: (val: number, record: InventoryMovement) => {
        const isNegative = ['SALE', 'TRANSFER_OUT'].includes(record.movement_type);
        return (
          <span style={{ color: isNegative ? '#cf1322' : '#389e0d' }}>
            {isNegative ? `-${Math.abs(val)}` : `+${val}`}
          </span>
        );
      },
    },
    {
      title: 'Referencia',
      key: 'reference',
      width: 150,
      render: (_: unknown, record: InventoryMovement) =>
        record.reference_type ? `${record.reference_type} #${record.reference_id}` : '-',
    },
    { title: 'Notas', dataIndex: 'notes', key: 'notes', ellipsis: true, render: (v) => v || '-' },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>Movimientos de Inventario</Title>

      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col>
          <Select
            allowClear
            placeholder="Producto"
            style={{ width: 250 }}
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
          <Select
            allowClear
            placeholder="Tipo movimiento"
            style={{ width: 200 }}
            onChange={(val) => setMovementType(val)}
            options={MOVEMENT_TYPES}
          />
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={movements ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />
    </div>
  );
}
