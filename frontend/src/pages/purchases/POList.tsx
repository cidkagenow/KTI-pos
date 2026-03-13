import { useState, useMemo, useRef } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  Divider,
  message,
  Popconfirm,
  Switch,
  Radio,
  DatePicker,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckOutlined,
  EyeOutlined,
  SearchOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getPurchaseOrders,
  createPurchaseOrder,
  updatePurchaseOrder,
  receivePurchaseOrder,
  deletePurchaseOrder,
} from '../../api/purchases';
import { getWarehouses, getSuppliers, createSupplier } from '../../api/catalogs';
import { lookupRUC } from '../../api/clients';
import { getProducts } from '../../api/products';
import dayjs from 'dayjs';
import { formatCurrency, formatDate } from '../../utils/format';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import { tokenizedFilter } from '../../utils/search';
import type { PurchaseOrder, PurchaseOrderItem } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'blue',
  RECEIVED: 'green',
  CANCELLED: 'red',
};

const CONDICION_COLORS: Record<string, string> = {
  CONTADO: 'green',
  CREDITO: 'orange',
};

interface POLineItem {
  key: string;
  product_id: number | null;
  product_code?: string;
  product_name?: string;
  quantity: number;
  unit_cost: number;
  discount_pct1: number;
  discount_pct2: number;
  discount_pct3: number;
  flete_unit: number;
  line_total: number;
}

/* ---------- line-level math ---------- */
function calcLineTotal(item: POLineItem): number {
  const price =
    item.unit_cost *
    (1 - (item.discount_pct1 || 0) / 100) *
    (1 - (item.discount_pct2 || 0) / 100) *
    (1 - (item.discount_pct3 || 0) / 100);
  return Math.round((item.quantity * price + item.quantity * (item.flete_unit || 0)) * 100) / 100;
}

function emptyLineItem(): POLineItem {
  return {
    key: crypto.randomUUID(),
    product_id: null,
    quantity: 1,
    unit_cost: 0,
    discount_pct1: 0,
    discount_pct2: 0,
    discount_pct3: 0,
    flete_unit: 0,
    line_total: 0,
  };
}

export default function POList() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPO, setEditingPO] = useState<PurchaseOrder | null>(null);
  const [viewOnly, setViewOnly] = useState(false);
  const [form] = Form.useForm();
  const autoAddItemRef = useRef<() => void>(() => {});
  const enterNavRef = useEnterNavigation(() => handleSubmit(), () => autoAddItemRef.current());
  const [items, setItems] = useState<POLineItem[]>([]);
  const [supplierModalOpen, setSupplierModalOpen] = useState(false);
  const [supplierForm] = Form.useForm();
  const [supplierLookupLoading, setSupplierLookupLoading] = useState(false);

  /* ---------- queries ---------- */
  const { data: orders, isLoading } = useQuery({
    queryKey: ['purchase-orders'],
    queryFn: () => getPurchaseOrders(),
  });

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: () => getProducts() });
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: getSuppliers });

  /* ---------- mutations ---------- */
  const createMut = useMutation({
    mutationFn: createPurchaseOrder,
    onSuccess: () => {
      message.success('Orden de compra creada');
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      closeModal();
    },
    onError: () => message.error('Error al crear orden'),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updatePurchaseOrder(id, data),
    onSuccess: () => {
      message.success('Orden actualizada');
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      closeModal();
    },
    onError: () => message.error('Error al actualizar orden'),
  });

  const receiveMut = useMutation({
    mutationFn: receivePurchaseOrder,
    onSuccess: () => {
      message.success('Orden recibida - stock actualizado');
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
    onError: () => message.error('Error al recibir orden'),
  });

  const deleteMut = useMutation({
    mutationFn: deletePurchaseOrder,
    onSuccess: () => {
      message.success('Orden eliminada');
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
    onError: () => message.error('Error al eliminar orden'),
  });

  const createSupplierMut = useMutation({
    mutationFn: createSupplier,
    onSuccess: (newSupplier) => {
      message.success('Proveedor creado');
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      form.setFieldValue('supplier_id', newSupplier.id);
      setSupplierModalOpen(false);
      supplierForm.resetFields();
    },
    onError: () => message.error('Error al crear proveedor'),
  });

  const handleSupplierLookup = async () => {
    const ruc = supplierForm.getFieldValue('ruc');
    if (!ruc || ruc.length !== 11) {
      message.warning('Ingrese un RUC válido de 11 dígitos');
      return;
    }
    setSupplierLookupLoading(true);
    try {
      const result = await lookupRUC(ruc);
      supplierForm.setFieldsValue({ business_name: result.business_name, address: result.address });
      message.success('Datos obtenidos de SUNAT');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al consultar SUNAT';
      message.error(detail);
    } finally {
      setSupplierLookupLoading(false);
    }
  };

  /* ---------- modal open / close ---------- */
  const openCreate = () => {
    setEditingPO(null);
    form.resetFields();
    form.setFieldsValue({
      doc_type: 'FACTURA',
      condicion: 'CONTADO',
      moneda: 'SOLES',
      tipo_cambio: 3.70,
      igv_included: true,
      flete: 0,
      expected_delivery_date: null,
    });
    setItems([emptyLineItem()]);
    setModalOpen(true);
  };

  const openEdit = (po: PurchaseOrder) => {
    setEditingPO(po);
    form.setFieldsValue({
      supplier_id: po.supplier_id,
      warehouse_id: po.warehouse_id,
      doc_type: po.doc_type ?? 'FACTURA',
      doc_number: po.doc_number,
      condicion: po.condicion ?? 'CONTADO',
      moneda: po.moneda ?? 'SOLES',
      tipo_cambio: po.tipo_cambio ?? 3.70,
      igv_included: po.igv_included ?? true,
      flete: po.flete ?? 0,
      grr_number: po.grr_number,
      expected_delivery_date: po.expected_delivery_date ? dayjs(po.expected_delivery_date) : null,
      notes: po.notes,
    });
    setItems(
      po.items.map((item) => ({
        key: crypto.randomUUID(),
        product_id: item.product_id,
        product_code: item.product_code,
        product_name: item.product_name,
        quantity: item.quantity,
        unit_cost: item.unit_cost,
        discount_pct1: item.discount_pct1 ?? 0,
        discount_pct2: item.discount_pct2 ?? 0,
        discount_pct3: item.discount_pct3 ?? 0,
        flete_unit: item.flete_unit ?? 0,
        line_total: item.line_total,
      }))
    );
    setModalOpen(true);
  };

  const openView = (po: PurchaseOrder) => {
    setEditingPO(po);
    setViewOnly(true);
    form.setFieldsValue({
      supplier_id: po.supplier_id,
      warehouse_id: po.warehouse_id,
      doc_type: po.doc_type ?? 'FACTURA',
      doc_number: po.doc_number,
      condicion: po.condicion ?? 'CONTADO',
      moneda: po.moneda ?? 'SOLES',
      tipo_cambio: po.tipo_cambio ?? 3.70,
      igv_included: po.igv_included ?? true,
      flete: po.flete ?? 0,
      grr_number: po.grr_number,
      expected_delivery_date: po.expected_delivery_date ? dayjs(po.expected_delivery_date) : null,
      notes: po.notes,
    });
    setItems(
      po.items.map((item) => ({
        key: crypto.randomUUID(),
        product_id: item.product_id,
        product_code: item.product_code,
        product_name: item.product_name,
        quantity: item.quantity,
        unit_cost: item.unit_cost,
        discount_pct1: item.discount_pct1 ?? 0,
        discount_pct2: item.discount_pct2 ?? 0,
        discount_pct3: item.discount_pct3 ?? 0,
        flete_unit: item.flete_unit ?? 0,
        line_total: item.line_total,
      }))
    );
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingPO(null);
    setViewOnly(false);
    form.resetFields();
    setItems([]);
  };

  /* ---------- line items manipulation ---------- */
  const addItem = () => {
    setItems((prev) => [...prev, emptyLineItem()]);
  };
  autoAddItemRef.current = addItem;

  const removeItem = (idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateItem = (idx: number, field: string, value: any) => {
    setItems((prev) => {
      const updated = [...prev];
      const item = { ...updated[idx], [field]: value };
      item.line_total = calcLineTotal(item);
      updated[idx] = item;
      return updated;
    });
  };

  /* ---------- footer totals ---------- */
  const igvIncluded = Form.useWatch('igv_included', form) ?? true;

  const { opGravada, igvAmount, orderTotal } = useMemo(() => {
    const sumLines = items.reduce((sum, item) => sum + item.line_total, 0);
    if (igvIncluded) {
      // Prices include IGV => back-calculate
      const base = Math.round((sumLines / 1.18) * 100) / 100;
      const igv = Math.round((sumLines - base) * 100) / 100;
      return { opGravada: base, igvAmount: igv, orderTotal: sumLines };
    } else {
      // Prices exclude IGV => add IGV
      const igv = Math.round(sumLines * 0.18 * 100) / 100;
      return { opGravada: sumLines, igvAmount: igv, orderTotal: Math.round((sumLines + igv) * 100) / 100 };
    }
  }, [items, igvIncluded]);

  /* ---------- submit ---------- */
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const validItems = items.filter((item) => item.product_id);
      if (validItems.length === 0) {
        message.error('Agregue al menos un producto');
        return;
      }
      const payload = {
        ...values,
        expected_delivery_date: values.expected_delivery_date
          ? dayjs(values.expected_delivery_date).format('YYYY-MM-DD')
          : null,
        subtotal: opGravada,
        igv_amount: igvAmount,
        total: orderTotal,
        items: validItems.map((item) => ({
          product_id: item.product_id,
          quantity: item.quantity,
          unit_cost: item.unit_cost,
          discount_pct1: item.discount_pct1,
          discount_pct2: item.discount_pct2,
          discount_pct3: item.discount_pct3,
          flete_unit: item.flete_unit,
          line_total: item.line_total,
        })),
      };
      if (editingPO) {
        updateMut.mutate({ id: editingPO.id, data: payload });
      } else {
        createMut.mutate(payload);
      }
    } catch {
      // form validation errors
    }
  };

  /* ---------- watched form fields ---------- */
  const moneda = Form.useWatch('moneda', form);

  /* ---------- main table columns ---------- */
  const columns: ColumnsType<PurchaseOrder> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    {
      title: 'Proveedor',
      key: 'supplier',
      ellipsis: true,
      render: (_: unknown, record: PurchaseOrder) => (
        <span>
          {record.supplier_name}
          {record.supplier_ruc ? (
            <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>
              ({record.supplier_ruc})
            </Text>
          ) : null}
        </span>
      ),
    },
    {
      title: 'Doc',
      key: 'doc',
      width: 160,
      render: (_: unknown, record: PurchaseOrder) => {
        if (!record.doc_type && !record.doc_number) return '-';
        return `${record.doc_type ?? ''} ${record.doc_number ?? ''}`.trim();
      },
    },
    {
      title: 'Productos',
      key: 'items',
      width: 200,
      ellipsis: true,
      render: (_: unknown, record: PurchaseOrder) => {
        if (!record.items || record.items.length === 0) return '-';
        return record.items.map((item, idx) => (
          <div key={idx} style={{ fontSize: 11, lineHeight: '16px' }}>
            {item.product_name || item.product_code} × <b>{item.quantity}</b>
          </div>
        ));
      },
    },
    {
      title: 'Almacen',
      key: 'warehouse_id',
      width: 130,
      render: (_: unknown, record: PurchaseOrder) => {
        const wh = warehouses?.find((w) => w.id === record.warehouse_id);
        return wh?.name ?? record.warehouse_id;
      },
    },
    {
      title: 'Estado',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => <Tag color={STATUS_COLORS[status] || 'default'}>{status}</Tag>,
    },
    {
      title: 'Condicion',
      dataIndex: 'condicion',
      key: 'condicion',
      width: 100,
      render: (val: string | null) =>
        val ? <Tag color={CONDICION_COLORS[val] || 'default'}>{val}</Tag> : '-',
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 110,
      align: 'right',
      render: (val: number | null) => (val != null ? formatCurrency(val) : '-'),
    },
    {
      title: 'Fecha',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 100,
      render: (val: string) => formatDate(val),
    },
    {
      title: 'Entrega Est.',
      dataIndex: 'expected_delivery_date',
      key: 'expected_delivery_date',
      width: 110,
      render: (val: string | null) => val ? formatDate(val) : '-',
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: PurchaseOrder) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => openView(record)}
          />
          {record.status === 'DRAFT' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => openEdit(record)}
              />
              <Popconfirm
                title="Recibir orden? Esto actualizara el stock."
                onConfirm={() => receiveMut.mutate(record.id)}
                okText="Si"
                cancelText="No"
              >
                <Button
                  type="link"
                  size="small"
                  icon={<CheckOutlined />}
                  style={{ color: '#52c41a' }}
                />
              </Popconfirm>
              <Popconfirm
                title="Eliminar orden?"
                onConfirm={() => deleteMut.mutate(record.id)}
                okText="Si"
                cancelText="No"
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  /* ---------- product select options ---------- */
  const productOptions = useMemo(
    () =>
      products
        ?.filter((p) => p.is_active)
        .map((p) => ({
          value: p.id,
          label: `${p.code} - ${p.name}`,
        })) ?? [],
    [products]
  );

  /* ---------- render ---------- */
  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            Ordenes de Compra
          </Title>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nueva Orden
          </Button>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={orders ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      {/* ====================== MODAL ====================== */}
      <Modal
        title={viewOnly ? 'Detalle Orden de Compra' : editingPO ? 'Editar Orden de Compra' : 'Nueva Orden de Compra'}
        open={modalOpen}
        onOk={viewOnly ? closeModal : handleSubmit}
        onCancel={closeModal}
        okText={viewOnly ? 'Cerrar' : 'Guardar'}
        cancelButtonProps={viewOnly ? { style: { display: 'none' } } : undefined}
        confirmLoading={!viewOnly && (createMut.isPending || updateMut.isPending)}
        width={960}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      >
        <div ref={enterNavRef}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }} disabled={viewOnly}>
          {/* --- Row 1: Doc Tipo, Nro Documento, Proveedor --- */}
          <Row gutter={12}>
            <Col span={5}>
              <Form.Item name="doc_type" label="Doc Tipo" rules={[{ required: true, message: 'Requerido' }]}>
                <Select
                  options={[
                    { value: 'FACTURA', label: 'FACTURA' },
                    { value: 'BOLETA', label: 'BOLETA' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={7}>
              <Form.Item name="doc_number" label="Nro Documento">
                <Input placeholder="Ej: F001-00012345" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="supplier_id"
                label="Proveedor"
                rules={[{ required: true, message: 'Requerido' }]}
              >
                <Select
                  showSearch
                  filterOption={tokenizedFilter}
                  placeholder="Seleccionar proveedor"
                  options={suppliers?.map((s) => ({
                    value: s.id,
                    label: s.ruc ? `${s.ruc} - ${s.business_name}` : s.business_name,
                  }))}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '4px 0' }} />
                      <Button
                        type="text"
                        icon={<PlusOutlined />}
                        onClick={() => setSupplierModalOpen(true)}
                        style={{ width: '100%' }}
                        size="small"
                      >
                        Nuevo Proveedor
                      </Button>
                    </>
                  )}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* --- Row 2: Condicion, Moneda, T.C. --- */}
          <Row gutter={12}>
            <Col span={6}>
              <Form.Item name="condicion" label="Condicion" rules={[{ required: true, message: 'Requerido' }]}>
                <Select
                  options={[
                    { value: 'CONTADO', label: 'CONTADO' },
                    { value: 'CREDITO', label: 'CREDITO' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="moneda" label="Moneda" rules={[{ required: true, message: 'Requerido' }]}>
                <Select
                  options={[
                    { value: 'SOLES', label: 'SOLES' },
                    { value: 'DOLARES', label: 'DOLARES' },
                  ]}
                />
              </Form.Item>
            </Col>
            {moneda === 'DOLARES' && (
              <Col span={5}>
                <Form.Item name="tipo_cambio" label="T.C.">
                  <InputNumber min={0} step={0.01} precision={2} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            )}
          </Row>

          {/* --- Row 3: IGV included, Flete Total, GRR N --- */}
          <Row gutter={12}>
            <Col span={7}>
              <Form.Item name="igv_included" label="Precio Unitario" valuePropName="value">
                <Radio.Group>
                  <Radio value={true}>Con IGV</Radio>
                  <Radio value={false}>Sin IGV</Radio>
                </Radio.Group>
              </Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item name="flete" label="Flete Total">
                <InputNumber min={0} step={0.01} precision={2} prefix="S/" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="grr_number" label="GRR N°">
                <Input placeholder="Guia de remision" />
              </Form.Item>
            </Col>
          </Row>

          {/* --- Row 4: Almacen, Entrega Estimada, Notas --- */}
          <Row gutter={12}>
            <Col span={7}>
              <Form.Item
                name="warehouse_id"
                label="Almacen"
                rules={[{ required: true, message: 'Requerido' }]}
              >
                <Select
                  placeholder="Seleccionar"
                  options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item name="expected_delivery_date" label="Fecha Entrega Est.">
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="dd/mm/aaaa" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="notes" label="Notas">
                <Input.TextArea rows={2} />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {/* ====================== LINE ITEMS ====================== */}
        <Divider style={{ margin: '4px 0 12px' }}>Productos</Divider>

        {/* Header row */}
        <Row gutter={6} style={{ marginBottom: 4, fontWeight: 600, fontSize: 12 }}>
          <Col span={6}>Producto</Col>
          <Col span={2} style={{ textAlign: 'center' }}>Cant.</Col>
          <Col span={3} style={{ textAlign: 'center' }}>Precio Unit.</Col>
          <Col span={2} style={{ textAlign: 'center' }}>%Dcto1</Col>
          <Col span={2} style={{ textAlign: 'center' }}>%Dcto2</Col>
          <Col span={2} style={{ textAlign: 'center' }}>%Dcto3</Col>
          <Col span={2} style={{ textAlign: 'center' }}>Flete U.</Col>
          <Col span={3} style={{ textAlign: 'right' }}>Importe</Col>
          <Col span={2} />
        </Row>

        {items.map((item, idx) => (
          <Row key={item.key} gutter={6} style={{ marginBottom: 6 }}>
            <Col span={6}>
              <Select
                showSearch
                filterOption={tokenizedFilter}
                placeholder="Producto"
                value={item.product_id}
                onChange={(val) => updateItem(idx, 'product_id', val)}
                options={productOptions}
                popupMatchSelectWidth={500}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={2}>
              <InputNumber
                min={1}
                value={item.quantity}
                onChange={(val) => updateItem(idx, 'quantity', val ?? 1)}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={3} data-enter-add-row>
              <InputNumber
                min={0}
                step={0.01}
                precision={2}
                value={item.unit_cost}
                onChange={(val) => updateItem(idx, 'unit_cost', val ?? 0)}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={2} data-enter-skip>
              <InputNumber
                min={0}
                max={100}
                step={0.5}
                precision={2}
                value={item.discount_pct1}
                onChange={(val) => updateItem(idx, 'discount_pct1', val ?? 0)}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={2} data-enter-skip>
              <InputNumber
                min={0}
                max={100}
                step={0.5}
                precision={2}
                value={item.discount_pct2}
                onChange={(val) => updateItem(idx, 'discount_pct2', val ?? 0)}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={2} data-enter-skip>
              <InputNumber
                min={0}
                max={100}
                step={0.5}
                precision={2}
                value={item.discount_pct3}
                onChange={(val) => updateItem(idx, 'discount_pct3', val ?? 0)}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={2} data-enter-skip>
              <InputNumber
                min={0}
                step={0.01}
                precision={2}
                value={item.flete_unit}
                onChange={(val) => updateItem(idx, 'flete_unit', val ?? 0)}
                style={{ width: '100%' }}
                size="small"
                disabled={viewOnly}
              />
            </Col>
            <Col span={3} data-enter-skip>
              <Input
                value={formatCurrency(item.line_total)}
                readOnly
                style={{ textAlign: 'right' }}
                size="small"
              />
            </Col>
            {!viewOnly && (
              <Col span={2}>
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => removeItem(idx)}
                  disabled={items.length <= 1}
                  size="small"
                />
              </Col>
            )}
          </Row>
        ))}

        {!viewOnly && (
          <Button
            type="dashed"
            onClick={addItem}
            icon={<PlusOutlined />}
            block
            style={{ marginTop: 8, marginBottom: 16 }}
          >
            Agregar Producto
          </Button>
        )}
        </div>

        {/* ====================== FOOTER TOTALS ====================== */}
        <Row justify="end" style={{ gap: 0 }}>
          <Col span={10}>
            <Row justify="space-between" style={{ marginBottom: 4 }}>
              <Text>Op. Gravada:</Text>
              <Text>{formatCurrency(opGravada)}</Text>
            </Row>
            <Row justify="space-between" style={{ marginBottom: 4 }}>
              <Text>IGV (18%):</Text>
              <Text>{formatCurrency(igvAmount)}</Text>
            </Row>
            <Divider style={{ margin: '4px 0' }} />
            <Row justify="space-between">
              <Text strong style={{ fontSize: 15 }}>
                Total:
              </Text>
              <Text strong style={{ fontSize: 15 }}>
                {formatCurrency(orderTotal)}
              </Text>
            </Row>
          </Col>
        </Row>
      </Modal>

      {/* ====================== SUPPLIER QUICK-CREATE MODAL ====================== */}
      <Modal
        title="Nuevo Proveedor"
        open={supplierModalOpen}
        onOk={() => supplierForm.validateFields().then((v) => createSupplierMut.mutate(v))}
        onCancel={() => { setSupplierModalOpen(false); supplierForm.resetFields(); }}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createSupplierMut.isPending}
        width={480}
        destroyOnClose
      >
        <Form form={supplierForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={12} align="bottom">
            <Col span={10}>
              <Form.Item name="ruc" label="RUC">
                <Input maxLength={11} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label=" ">
                <Button
                  icon={supplierLookupLoading ? <LoadingOutlined /> : <SearchOutlined />}
                  onClick={handleSupplierLookup}
                  loading={supplierLookupLoading}
                  size="small"
                >
                  Buscar SUNAT
                </Button>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={24}>
              <Form.Item name="business_name" label="Razon Social" rules={[{ required: true, message: 'Requerido' }]}>
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={24}>
              <Form.Item name="address" label="Direccion">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="phone" label="Telefono">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="city" label="Ciudad">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="email" label="Email">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
