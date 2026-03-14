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
import { PlusOutlined, SwapOutlined } from '@ant-design/icons';
import SearchInput from '../../components/SearchInput';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getInventory, adjustStock, transferStock } from '../../api/inventory';
import { getWarehouses } from '../../api/catalogs';
import { getProducts } from '../../api/products';
import { tokenizedFilter, tokenizedFilterSort } from '../../utils/search';
import { formatCurrency } from '../../utils/format';
import type { InventoryItem } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import useFuzzyFilter from '../../hooks/useFuzzyFilter';

const { Title } = Typography;

export default function StockLevels() {
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState<number | undefined>(1);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [transferForm] = Form.useForm();
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

  const transferMutation = useMutation({
    mutationFn: transferStock,
    onSuccess: async () => {
      message.success('Transferencia realizada');
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ['inventory'] }),
        queryClient.refetchQueries({ queryKey: ['products'] }),
      ]);
      setTransferModalOpen(false);
      transferForm.resetFields();
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail || 'Error al transferir stock';
      message.error(detail);
    },
  });

  const handleTransfer = async () => {
    try {
      const values = await transferForm.validateFields();
      transferMutation.mutate(values);
    } catch {
      // validation failed
    }
  };

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
      return product ? item.quantity <= product.min_stock : false;
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
        const isLow = product ? record.quantity <= product.min_stock : false;
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
          <Space>
            <Button icon={<SwapOutlined />} onClick={() => setTransferModalOpen(true)}>
              Transferir
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAdjustModalOpen(true)}>
              Ajustar Stock
            </Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={16} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <SearchInput
            value={search}
            onChange={setSearch}
            suggestion={fuzzyFiltered.length > 0 ? fuzzyFiltered[0].product_name : undefined}
            placeholder="Buscar por codigo o nombre..."
            style={{ width: 250 }}
          />
        </Col>
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
              filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
              popupMatchSelectWidth={500}
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

      {/* ---- Transfer Modal ---- */}
      <Modal
        title="Transferir Stock"
        open={transferModalOpen}
        onOk={handleTransfer}
        onCancel={() => { setTransferModalOpen(false); transferForm.resetFields(); }}
        okText="Transferir"
        cancelText="Cancelar"
        confirmLoading={transferMutation.isPending}
      >
        <Form form={transferForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="product_id" label="Producto" rules={[{ required: true, message: 'Requerido' }]}>
            <Select
              showSearch
              placeholder="Seleccionar producto"
              filterOption={tokenizedFilter}
              filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
              popupMatchSelectWidth={500}
              options={products?.filter((p) => p.is_active).map((p) => ({
                value: p.id,
                label: `${p.code} - ${p.name}`,
              }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="from_warehouse_id" label="Desde Almacen" rules={[{ required: true, message: 'Requerido' }]}>
                <Select
                  placeholder="Origen"
                  options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="to_warehouse_id" label="Hacia Almacen" rules={[{ required: true, message: 'Requerido' }]}>
                <Select
                  placeholder="Destino"
                  options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="quantity" label="Cantidad" rules={[{ required: true, message: 'Requerido' }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
