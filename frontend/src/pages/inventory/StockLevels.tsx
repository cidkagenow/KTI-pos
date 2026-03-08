import { useState } from 'react';
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
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getInventory, adjustStock } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import { getProducts } from '../../api/products';
import type { InventoryItem } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

export default function StockLevels() {
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: inventory, isLoading } = useQuery({
    queryKey: ['inventory', warehouseId],
    queryFn: () => getInventory(warehouseId ? { warehouse_id: warehouseId } : undefined),
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

  const filteredData = lowStockOnly
    ? (inventory ?? []).filter((item) => {
        const product = products?.find((p) => p.id === item.product_id);
        return product ? item.quantity < product.min_stock : false;
      })
    : (inventory ?? []);

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

      <Row gutter={16} style={{ marginBottom: 16 }}>
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
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="product_id" label="Producto" rules={[{ required: true, message: 'Requerido' }]}>
            <Select
              showSearch
              placeholder="Seleccionar producto"
              optionFilterProp="label"
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
      </Modal>
    </div>
  );
}
