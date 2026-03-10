import { useState, useMemo } from 'react';
import {
  Table,
  Select,
  Input,
  Typography,
  Row,
  Col,
  Card,
  Statistic,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { getInventory } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import { getProducts } from '../../api/products';
import { formatCurrency } from '../../utils/format';
import type { InventoryItem } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

export default function StockValorizado() {
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [search, setSearch] = useState('');

  const { data: inventory, isLoading } = useQuery({
    queryKey: ['inventory', warehouseId],
    queryFn: () => getInventory(warehouseId ? { warehouse_id: warehouseId } : undefined),
  });

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: () => getProducts() });

  const filteredData = useMemo(() => {
    let data = inventory ?? [];
    if (search) {
      const terms = search.toLowerCase().split(/\s+/);
      data = data.filter((item) => {
        const text = `${item.product_code} ${item.product_name}`.toLowerCase();
        return terms.every((t) => text.includes(t));
      });
    }
    return data;
  }, [inventory, search]);

  const getCostPrice = (productId: number) => {
    return products?.find((p) => p.id === productId)?.cost_price ?? 0;
  };

  const totals = useMemo(() => {
    return (filteredData ?? []).reduce(
      (acc, item) => {
        const cost = getCostPrice(item.product_id);
        return {
          units: acc.units + item.quantity,
          value: acc.value + item.quantity * cost,
        };
      },
      { units: 0, value: 0 },
    );
  }, [filteredData, products]);

  const columns: ColumnsType<InventoryItem> = [
    { title: 'Codigo', dataIndex: 'product_code', key: 'product_code', width: 100, sorter: (a, b) => a.product_code.localeCompare(b.product_code) },
    { title: 'Producto', dataIndex: 'product_name', key: 'product_name', ellipsis: true, sorter: (a, b) => a.product_name.localeCompare(b.product_name) },
    { title: 'Almacen', dataIndex: 'warehouse_name', key: 'warehouse_name', width: 150, sorter: (a, b) => a.warehouse_name.localeCompare(b.warehouse_name) },
    {
      title: 'Cantidad',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      align: 'right',
      sorter: (a, b) => a.quantity - b.quantity,
    },
    {
      title: 'Costo Unit.',
      key: 'cost_price',
      width: 120,
      align: 'right',
      render: (_: unknown, record: InventoryItem) => formatCurrency(getCostPrice(record.product_id)),
      sorter: (a, b) => getCostPrice(a.product_id) - getCostPrice(b.product_id),
    },
    {
      title: 'Valor Total',
      key: 'valor_total',
      width: 130,
      align: 'right',
      render: (_: unknown, record: InventoryItem) => formatCurrency(record.quantity * getCostPrice(record.product_id)),
      sorter: (a, b) => (a.quantity * getCostPrice(a.product_id)) - (b.quantity * getCostPrice(b.product_id)),
      defaultSortOrder: 'descend',
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Stock Valorizado</Title>
        </Col>
      </Row>

      <Row gutter={16} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Input
            placeholder="Buscar por codigo o nombre..."
            prefix={<SearchOutlined />}
            allowClear
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 250 }}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="Filtrar por almacen"
            style={{ width: 200 }}
            onChange={(val) => setWarehouseId(val)}
            options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
          />
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Row gutter={16} justify="end">
            <Col>
              <Card size="small" style={{ display: 'inline-block' }}>
                <Statistic
                  title="Total Unidades"
                  value={totals.units}
                  valueStyle={{ fontSize: 18, fontWeight: 600 }}
                />
              </Card>
            </Col>
            <Col>
              <Card size="small" style={{ display: 'inline-block' }}>
                <Statistic
                  title="Stock Valorizado"
                  value={totals.value}
                  precision={2}
                  prefix="S/"
                  valueStyle={{ fontSize: 18, fontWeight: 600 }}
                />
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />
    </div>
  );
}
