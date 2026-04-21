import { useState, useRef } from 'react';
import {
  Table,
  Button,
  Input,
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
  Space,
  Tag,
  Tooltip,
  Typography,
  Row,
  Col,
  Upload,
  Image,
  message,
  Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, GlobalOutlined, CloudUploadOutlined, CameraOutlined } from '@ant-design/icons';
import SearchInput from '../../components/SearchInput';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProducts, createProduct, updateProduct, deleteProduct, syncOnlineProducts, getNextProductCode, uploadProductImage } from '../../api/products';
import { getBrands, getCategories } from '../../api/catalogs';
import { adjustStock } from '../../api/inventory';
import { formatCurrency } from '../../utils/format';
import { tokenizedFilter, tokenizedFilterSort } from '../../utils/search';
import { useAuth } from '../../contexts/AuthContext';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import useFuzzyFilter from '../../hooks/useFuzzyFilter';
import type { Product } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

export default function ProductList() {
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const [search, setSearch] = useState('');
  const [filterBrand, setFilterBrand] = useState<number | undefined>(undefined);
  const [filterCategory, setFilterCategory] = useState<number | undefined>(undefined);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [form] = Form.useForm();
  const nameInputRef = useRef<any>(null);
  const enterNavRef = useEnterNavigation(() => handleSubmit());
  const [editingStockId, setEditingStockId] = useState<number | null>(null);
  const [editingStockValue, setEditingStockValue] = useState<number>(0);
  const [previewId, setPreviewId] = useState<number | null>(null);

  const adjustMutation = useMutation({
    mutationFn: (data: { product_id: number; new_quantity: number }) =>
      adjustStock({ product_id: data.product_id, warehouse_id: 1, new_quantity: data.new_quantity, notes: 'Ajuste desde lista de productos' }),
    onMutate: (data) => {
      // Optimistic update: immediately show new stock value
      queryClient.setQueriesData<Product[]>({ queryKey: ['products'] }, (old) =>
        old?.map((p) => (p.id === data.product_id ? { ...p, total_stock: data.new_quantity } : p)),
      );
      setEditingStockId(null);
    },
    onSuccess: () => {
      message.success('Stock actualizado');
    },
    onError: () => {
      message.error('Error al ajustar stock');
      // Revert on error by refetching
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });

  const { data: allProducts, isLoading } = useQuery({
    queryKey: ['products', filterBrand, filterCategory],
    refetchInterval: 30_000,
    queryFn: () => {
      const params: { brand_id?: number; category_id?: number } = {};
      if (filterBrand) params.brand_id = filterBrand;
      if (filterCategory) params.category_id = filterCategory;
      return getProducts(Object.keys(params).length > 0 ? params : undefined);
    },
  });

  const products = useFuzzyFilter(allProducts ?? [], search, (p) =>
    `${p.code} ${p.name} ${p.brand_name || ''} ${p.category_name || ''}`
  );

  const { data: brands } = useQuery({ queryKey: ['brands'], queryFn: getBrands });
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: getCategories });

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      message.success('Producto creado');
      queryClient.invalidateQueries({ queryKey: ['products'] });
      closeModal();
    },
    onError: () => message.error('Error al crear producto'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateProduct(id, data),
    onSuccess: () => {
      message.success('Producto actualizado');
      queryClient.invalidateQueries({ queryKey: ['products'] });
      closeModal();
    },
    onError: () => message.error('Error al actualizar producto'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => {
      message.success('Producto eliminado');
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError: () => message.error('Error al eliminar producto'),
  });

  const syncMutation = useMutation({
    mutationFn: syncOnlineProducts,
    onSuccess: (data) => {
      message.success(`Sincronizado: ${data.synced_products} productos enviados a la tienda web`);
    },
    onError: () => message.error('Error al sincronizar con la tienda web'),
  });

  const openCreate = async () => {
    setEditingProduct(null);
    form.resetFields();
    setModalOpen(true);
    try {
      const code = await getNextProductCode();
      form.setFieldValue('code', code);
    } catch { /* user can type manually */ }
    setTimeout(() => nameInputRef.current?.focus(), 100);
  };

  const openEdit = (product: Product) => {
    setEditingProduct(product);
    form.setFieldsValue({
      code: product.code,
      name: product.name,
      brand_id: product.brand_id,
      category_id: product.category_id,
      presentation: product.presentation,
      unit_price: product.unit_price,
      wholesale_price: product.wholesale_price,
      cost_price: product.cost_price,
      min_stock: product.min_stock,
      comentario: product.comentario,
      is_online: product.is_online,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingProduct(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingProduct) {
        updateMutation.mutate({ id: editingProduct.id, data: values });
      } else {
        createMutation.mutate(values);
      }
    } catch {
      // validation failed
    }
  };

  const getStockColor = (stock: number, minStock: number): string => {
    if (stock < 0) return '#ff4d4f';
    if (stock <= minStock) return '#faad14';
    return '#52c41a';
  };

  const columns: ColumnsType<Product> = [
    {
      title: '',
      key: 'image',
      width: 50,
      render: (_: unknown, record: Product) =>
        record.image_url ? (
          <Image
            src={record.image_url}
            width={36}
            height={36}
            style={{ objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }}
            preview={{
              visible: previewId === record.id,
              onVisibleChange: (vis) => setPreviewId(vis ? record.id : null),
              mask: false,
            }}
            fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzYiIGhlaWdodD0iMzYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjM2IiBoZWlnaHQ9IjM2IiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+"
          />
        ) : (
          <div style={{ width: 36, height: 36, borderRadius: 4, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CameraOutlined style={{ color: '#bbb', fontSize: 14 }} />
          </div>
        ),
    },
    { title: 'Codigo', dataIndex: 'code', key: 'code', width: 80 },
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    { title: 'Marca', dataIndex: 'brand_name', key: 'brand_name', width: 120, render: (v) => v || '-' },
    { title: 'Categoria', dataIndex: 'category_name', key: 'category_name', width: 120, render: (v) => v || '-' },
    { title: 'Presentacion', dataIndex: 'presentation', key: 'presentation', width: 120, render: (v) => v || '-' },
    {
      title: 'Stock Total',
      dataIndex: 'total_stock',
      key: 'total_stock',
      width: 110,
      align: 'right',
      render: (stock: number, record: Product) =>
        isAdmin && editingStockId === record.id ? (
          <InputNumber
            size="small"
            autoFocus
            value={editingStockValue}
            onChange={(v) => setEditingStockValue(v ?? 0)}
            onPressEnter={() => {
              Modal.confirm({
                title: 'Confirmar Ajuste de Stock',
                content: (
                  <div>
                    <p>Modificar stock directamente:</p>
                    <p><strong>{record.code} - {record.name}</strong></p>
                    <p>Stock actual: {stock} → Nuevo: {editingStockValue}</p>
                    <p style={{ color: '#faad14', marginTop: 8 }}>Solo usar para correciones de inventario fisico.</p>
                  </div>
                ),
                okText: 'Aplicar',
                cancelText: 'Cancelar',
                onOk: () => adjustMutation.mutate({ product_id: record.id, new_quantity: editingStockValue }),
                onCancel: () => setEditingStockId(null),
              });
            }}
            onBlur={() => setEditingStockId(null)}
            style={{ width: 80 }}
          />
        ) : (
          <span
            style={{ color: getStockColor(stock, record.min_stock), fontWeight: 600, cursor: isAdmin ? 'pointer' : 'default' }}
            onClick={isAdmin ? () => { setEditingStockId(record.id); setEditingStockValue(stock); } : undefined}
          >
            {stock}
          </span>
        ),
    },
    ...(isAdmin
      ? [
          {
            title: 'Costo Uni',
            dataIndex: 'cost_price',
            key: 'cost_price',
            width: 110,
            align: 'right' as const,
            render: (val: number | null) => (val != null ? formatCurrency(val) : '-'),
          },
        ]
      : []),
    {
      title: 'P.V.P',
      dataIndex: 'unit_price',
      key: 'unit_price',
      width: 110,
      align: 'right',
      render: (val: number) => formatCurrency(val),
    },
    {
      title: 'P.MAY',
      dataIndex: 'wholesale_price',
      key: 'wholesale_price',
      width: 110,
      align: 'right',
      render: (val: number | null) => (val != null ? formatCurrency(val) : '-'),
    },
    {
      title: 'Comentario',
      dataIndex: 'comentario',
      key: 'comentario',
      width: 150,
      ellipsis: true,
      render: (v: string | null) => v || '-',
    },
    {
      title: 'Web',
      key: 'is_online',
      width: 50,
      align: 'center',
      render: (_: unknown, record: Product) =>
        record.is_online ? <GlobalOutlined style={{ color: '#1890ff' }} /> : null,
    },
    {
      title: 'Estado',
      key: 'estado',
      width: 130,
      render: (_: unknown, record: Product) => {
        if (!record.is_active) {
          return <Tag color="red">Inactivo</Tag>;
        }
        if (record.total_stock <= 0) {
          if (record.on_order_qty) {
            const etaStr = record.on_order_eta
              ? new Date(record.on_order_eta).toLocaleDateString('es-PE')
              : 'Sin fecha';
            return (
              <Tooltip title={`Llega: ${etaStr}`}>
                <Tag color="orange">En Pedido ({record.on_order_qty})</Tag>
              </Tooltip>
            );
          }
          return <Tag color="red">Agotado</Tag>;
        }
        return <Tag color="green">Activo</Tag>;
      },
    },
    ...(isAdmin
      ? [
          {
            title: 'Acciones',
            key: 'actions',
            width: 100,
            fixed: 'right' as const,
            render: (_: unknown, record: Product) => (
              <Space size="small">
                <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
                <Popconfirm
                  title="Eliminar producto?"
                  onConfirm={() => deleteMutation.mutate(record.id)}
                  okText="Si"
                  cancelText="No"
                >
                  <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Productos</Title>
        </Col>
        <Col>
          <Space>
            <SearchInput
              value={search}
              onChange={setSearch}
              suggestion={products.length > 0 ? products[0].name : undefined}
              placeholder="Buscar productos..."
              style={{ width: 250 }}
              autoFocus
            />
            <Select
              placeholder="Marca"
              allowClear
              showSearch
              filterOption={tokenizedFilter}
              filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
              style={{ width: 150 }}
              value={filterBrand}
              onChange={(val) => setFilterBrand(val)}
              options={brands?.map((b) => ({ value: b.id, label: b.name }))}
            />
            <Select
              placeholder="Categoria"
              allowClear
              showSearch
              filterOption={tokenizedFilter}
              filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
              style={{ width: 150 }}
              value={filterCategory}
              onChange={(val) => setFilterCategory(val)}
              options={categories?.map((c) => ({ value: c.id, label: c.name }))}
            />
            {isAdmin && (
              <>
                <Button
                  icon={<CloudUploadOutlined />}
                  onClick={() => syncMutation.mutate()}
                  loading={syncMutation.isPending}
                >
                  Sincronizar Tienda Web
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                  Nuevo Producto
                </Button>
              </>
            )}
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={products ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        scroll={{ x: 1400 }}
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      <Modal
        title={editingProduct ? 'Editar Producto' : 'Nuevo Producto'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={closeModal}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={700}
      >
        <div ref={enterNavRef}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {editingProduct && (
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
              {editingProduct.image_url ? (
                <Image
                  src={editingProduct.image_url}
                  width={80}
                  height={80}
                  style={{ objectFit: 'cover', borderRadius: 8 }}
                />
              ) : (
                <div style={{ width: 80, height: 80, borderRadius: 8, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CameraOutlined style={{ fontSize: 24, color: '#bbb' }} />
                </div>
              )}
              <Upload
                accept="image/jpeg,image/png,image/webp"
                showUploadList={false}
                customRequest={async ({ file, onSuccess, onError }) => {
                  try {
                    await uploadProductImage(editingProduct.id, file as File);
                    message.success('Imagen actualizada');
                    queryClient.invalidateQueries({ queryKey: ['products'] });
                    onSuccess?.(null);
                  } catch {
                    message.error('Error al subir imagen');
                    onError?.(new Error('Upload failed'));
                  }
                }}
              >
                <Button icon={<CameraOutlined />} size="small">Cambiar Imagen</Button>
              </Upload>
            </div>
          )}
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="code" label="Codigo" rules={[{ required: true, message: 'Requerido' }]}>
                <Input disabled={!editingProduct} />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'Requerido' }]}>
                <Input ref={nameInputRef} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="brand_id" label="Marca">
                <Select
                  allowClear
                  showSearch
                  filterOption={tokenizedFilter}
                  filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
                  placeholder="Seleccionar"
                  options={brands?.filter((b) => b.is_active).map((b) => ({ value: b.id, label: b.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="category_id" label="Categoria">
                <Select
                  allowClear
                  showSearch
                  filterOption={tokenizedFilter}
                  filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
                  placeholder="Seleccionar"
                  options={categories?.filter((c) => c.is_active).map((c) => ({ value: c.id, label: c.name }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="presentation" label="Presentacion">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="min_stock" label="Stock Minimo" initialValue={0}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="cost_price" label="Costo Unitario">
                <InputNumber min={0} step={0.01} prefix="S/" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="unit_price"
                label="P.V.P"
                rules={[{ required: true, message: 'Requerido' }]}
              >
                <InputNumber min={0} step={0.01} prefix="S/" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="wholesale_price" label="P.MAY (Mayoreo)">
                <InputNumber min={0} step={0.01} prefix="S/" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={18}>
              <Form.Item name="comentario" label="Comentario">
                <Input.TextArea rows={2} placeholder="Nota o comentario sobre el producto" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_online" label="Visible en Tienda Web" valuePropName="checked" initialValue={false}>
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
        </div>
      </Modal>
    </div>
  );
}
