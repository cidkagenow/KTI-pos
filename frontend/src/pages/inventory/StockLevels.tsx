import { useState, useMemo } from 'react';
import {
  Table,
  Button,
  Select,
  Switch,
  Modal,
  Form,
  InputNumber,
  Input,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  message,
  Card,
  Statistic,
} from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getInventory, adjustStock } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import { getProducts } from '../../api/products';
import { tokenizedFilter } from '../../utils/search';
import { formatCurrency } from '../../utils/format';
import type { InventoryItem } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import useFuzzyFilter from '../../hooks/useFuzzyFilter';

const { Title } = Typography;

export default function StockLevels() {
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [form] = Form.useForm();
  const enterNavRef = useEnterNavigation(() => handleAdjust());

  const { data: inventory, isLoading } = useQuery({
    queryKey: ['inventory', warehouseId],
    queryFn: () => getInventory(warehouseId ? { warehouse_id: warehouseId } : undefined),
    refetchInterval: 30_000,
  });

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: () => getProducts() });

  const adjustMutation = useMutation({
    mutationFn: adjustStock,
    onSuccess: async () => {
      message.success('Stock ajustado correctamente');
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ['inventory'] }),
        queryClient.refetchQueries({ queryKey: ['products'] }),
      ]);
      setAdjustModalOpen(false);
      form.resetFields();
    },
    onError: () => message.error('Error al ajustar stock'),
  });

  const handleAdjust = async () => {
    try {
      const values = await form.validateFields();
      adjustMutation.mutate(values);
    } catch {
      // validation failed
    }
  };

  const fuzzyFiltered = useFuzzyFilter(inventory ?? [], search, (item) =>
    `${item.product_code} ${item.product_name}`
  );

  const filteredData = useMemo(() => {
    if (!lowStockOnly) return fuzzyFiltered;
    return fuzzyFiltered.filter((item) => {
      const product = products?.find((p) => p.id === item.product_id);
      return product ? item.quantity < product.min_stock : false;
    });
  }, [fuzzyFiltered, lowStockOnly, products]);

  const stockValorizado = useMemo(() => {
    return (filteredData ?? []).reduce((sum, item) => {
      const product = products?.find((p) => p.id === item.product_id);
      const cost = product?.cost_price ?? 0;
      return sum + item.quantity * cost;
    }, 0);
  }, [filteredData, products]);

  const columns: ColumnsType<InventoryItem> = [
    { title: 'Codigo', dataIndex: 'product_code', key: 'product_code', width: 100 },
    { title: 'Producto', dataIndex: 'product_name', key: 'product_name', ellipsis: true },
    { title: 'Almacen', dataIndex: 'warehouse_name', key: 'warehouse_name', width: 150 },
    {
      title: 'Cantidad',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      align: 'right',
    },
    {
      title: 'Estado',
      key: 'status',
      width: 110,
      render: (_: unknown, record: InventoryItem) => {
        const product = products?.find((p) => p.id === record.product_id);
        const isLow = product ? record.quantity < product.min_stock : false;
        return (
          <Tag color={isLow ? 'red' : 'green'}>
            {isLow ? 'Stock Bajo' : 'Normal'}
          </Tag>
        );
      },
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Stock por Almacen</Title>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAdjustModalOpen(true)}>
            Ajustar Stock
          </Button>
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
        <Col>
          <Space>
            <Switch checked={lowStockOnly} onChange={setLowStockOnly} />
            <span>Solo stock bajo</span>
          </Space>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Card size="small" style={{ display: 'inline-block' }}>
            <Statistic
              title="Stock Valorizado"
              value={stockValorizado}
              precision={2}
              prefix="S/"
              valueStyle={{ fontSize: 18, fontWeight: 600 }}
            />
          </Card>
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

      <Modal
        title="Ajustar Stock"
        open={adjustModalOpen}
        onOk={handleAdjust}
        onCancel={() => { setAdjustModalOpen(false); form.resetFields(); }}
        okText="Aplicar"
        cancelText="Cancelar"
        confirmLoading={adjustMutation.isPending}
      >
        <div ref={enterNavRef}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="product_id" label="Producto" rules={[{ required: true, message: 'Requerido' }]}>
            <Select
              showSearch
              placeholder="Seleccionar producto"
              filterOption={tokenizedFilter}
              options={products?.filter((p) => p.is_active).map((p) => ({
                value: p.id,
                label: `${p.code} - ${p.name}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="warehouse_id" label="Almacen" rules={[{ required: true, message: 'Requerido' }]}>
            <Select
              placeholder="Seleccionar almacen"
              options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
            />
          </Form.Item>
          <Form.Item name="new_quantity" label="Nueva Cantidad" rules={[{ required: true, message: 'Requerido' }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="Notas">
            <Input.TextArea rows={2} placeholder="Motivo del ajuste" />
          </Form.Item>
        </Form>
        </div>
      </Modal>
    </div>
  );
}
