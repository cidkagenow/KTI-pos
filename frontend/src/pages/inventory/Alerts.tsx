import { useState } from 'react';
import { Table, Tag, Typography, Spin, Select, Row, Col } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getAlerts } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import type { InventoryItem } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

export default function Alerts() {
  const [warehouseId, setWarehouseId] = useState<number | undefined>(1);

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['inventory-alerts', warehouseId],
    queryFn: () => getAlerts(warehouseId ? { warehouse_id: warehouseId } : undefined),
    refetchInterval: 30_000,
  });

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });

  const columns: ColumnsType<InventoryItem> = [
    { title: 'Codigo', dataIndex: 'product_code', key: 'product_code', width: 100 },
    { title: 'Producto', dataIndex: 'product_name', key: 'product_name', ellipsis: true },
    { title: 'Almacen', dataIndex: 'warehouse_name', key: 'warehouse_name', width: 150 },
    {
      title: 'Stock Actual',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 120,
      align: 'right',
      render: (val: number) => (
        <Tag color="red">{val}</Tag>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Alertas de Stock Bajo
      </Title>

      <Row style={{ marginBottom: 16 }}>
        <Col>
          <Select
            allowClear
            placeholder="Todos los almacenes"
            style={{ width: 200 }}
            value={warehouseId}
            onChange={(val) => setWarehouseId(val)}
            options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
          />
        </Col>
      </Row>

      {alerts && alerts.length === 0 ? (
        <Typography.Text type="secondary">
          No hay productos con stock bajo.
        </Typography.Text>
      ) : (
        <Table
          columns={columns}
          dataSource={alerts ?? []}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      )}
    </div>
  );
}
