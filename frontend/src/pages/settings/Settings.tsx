import { useState } from 'react';
import {
  Tabs,
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
  message,
  Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, LoadingOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getBrands,
  createBrand,
  updateBrand,
  deleteBrand,
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  getWarehouses,
  createWarehouse,
  updateWarehouse,
  deleteWarehouse,
  getDocumentSeries,
  createDocumentSeries,
  updateDocumentSeries,
  getSuppliers,
  createSupplier,
  updateSupplier,
  deleteSupplier,
} from '../../api/catalogs';
import { lookupRUC } from '../../api/clients';
import type { Brand, Category, Warehouse, DocumentSeries, Supplier } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

/* ============================================================
   Generic CRUD Tab
   ============================================================ */
interface CrudTabProps<T extends { id: number; is_active?: boolean }> {
  queryKey: string;
  fetchFn: () => Promise<T[]>;
  createFn: (data: any) => Promise<T>;
  updateFn: (id: number, data: any) => Promise<T>;
  deleteFn: (id: number) => Promise<void>;
  columns: ColumnsType<T>;
  formFields: React.ReactNode;
  title: string;
  onEdit: (record: T, form: any) => void;
}

function CrudTab<T extends { id: number; is_active?: boolean }>({
  queryKey,
  fetchFn,
  createFn,
  updateFn,
  deleteFn,
  columns,
  formFields,
  title,
  onEdit,
}: CrudTabProps<T>) {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const { data, isLoading } = useQuery({ queryKey: [queryKey], queryFn: fetchFn });

  const createMut = useMutation({
    mutationFn: createFn,
    onSuccess: () => { message.success(`${title} creado`); qc.invalidateQueries({ queryKey: [queryKey] }); close(); },
    onError: () => message.error(`Error al crear ${title.toLowerCase()}`),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, d }: { id: number; d: any }) => updateFn(id, d),
    onSuccess: () => { message.success(`${title} actualizado`); qc.invalidateQueries({ queryKey: [queryKey] }); close(); },
    onError: () => message.error(`Error al actualizar ${title.toLowerCase()}`),
  });

  const deleteMut = useMutation({
    mutationFn: deleteFn,
    onSuccess: () => { message.success(`${title} eliminado`); qc.invalidateQueries({ queryKey: [queryKey] }); },
    onError: () => message.error(`Error al eliminar ${title.toLowerCase()}`),
  });

  const close = () => { setModalOpen(false); setEditingId(null); form.resetFields(); };

  const openCreate = () => { setEditingId(null); form.resetFields(); setModalOpen(true); };

  const openEditRecord = (record: T) => {
    setEditingId(record.id);
    onEdit(record, form);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingId) {
        updateMut.mutate({ id: editingId, d: values });
      } else {
        createMut.mutate(values);
      }
    } catch { /* validation */ }
  };

  const allColumns: ColumnsType<T> = [
    ...columns,
    {
      title: 'Acciones',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: T) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditRecord(record)} />
          <Popconfirm title="Eliminar?" onConfirm={() => deleteMut.mutate(record.id)} okText="Si" cancelText="No">
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="end" style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} size="small">
          Nuevo
        </Button>
      </Row>
      <Table columns={allColumns} dataSource={(data ?? []) as T[]} rowKey="id" loading={isLoading} size="small" pagination={false} />
      <Modal
        title={editingId ? `Editar ${title}` : `Nuevo ${title}`}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={close}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createMut.isPending || updateMut.isPending}
        width={450}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {formFields}
        </Form>
      </Modal>
    </div>
  );
}

/* ============================================================
   Supplier Tab (dedicated, with SUNAT lookup)
   ============================================================ */
function SupplierTab() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [form] = Form.useForm();

  const rucValue: string | undefined = Form.useWatch('ruc', form);
  const canLookup = rucValue?.length === 11;

  const { data, isLoading } = useQuery({ queryKey: ['suppliers'], queryFn: getSuppliers });

  const createMut = useMutation({
    mutationFn: createSupplier,
    onSuccess: () => { message.success('Proveedor creado'); qc.invalidateQueries({ queryKey: ['suppliers'] }); close(); },
    onError: () => message.error('Error al crear proveedor'),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, d }: { id: number; d: any }) => updateSupplier(id, d),
    onSuccess: () => { message.success('Proveedor actualizado'); qc.invalidateQueries({ queryKey: ['suppliers'] }); close(); },
    onError: () => message.error('Error al actualizar proveedor'),
  });

  const deleteMut = useMutation({
    mutationFn: deleteSupplier,
    onSuccess: () => { message.success('Proveedor eliminado'); qc.invalidateQueries({ queryKey: ['suppliers'] }); },
    onError: () => message.error('Error al eliminar proveedor'),
  });

  const close = () => { setModalOpen(false); setEditingId(null); form.resetFields(); };

  const openCreate = () => { setEditingId(null); form.resetFields(); setModalOpen(true); };

  const openEdit = (record: Supplier) => {
    setEditingId(record.id);
    form.setFieldsValue({
      ruc: record.ruc,
      business_name: record.business_name,
      city: record.city,
      phone: record.phone,
      email: record.email,
      address: record.address,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingId) {
        updateMut.mutate({ id: editingId, d: values });
      } else {
        createMut.mutate(values);
      }
    } catch { /* validation */ }
  };

  const handleLookup = async () => {
    setLookupLoading(true);
    try {
      const result = await lookupRUC(rucValue!);
      form.setFieldsValue({ business_name: result.business_name, address: result.address });
      message.success('Datos obtenidos correctamente');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al consultar SUNAT';
      message.error(detail);
    } finally {
      setLookupLoading(false);
    }
  };

  const columns: ColumnsType<Supplier> = [
    { title: 'RUC', dataIndex: 'ruc', key: 'ruc', width: 120, render: (v) => v || '-' },
    { title: 'Razon Social', dataIndex: 'business_name', key: 'business_name' },
    { title: 'Ciudad', dataIndex: 'city', key: 'city', render: (v) => v || '-' },
    { title: 'Telefono', dataIndex: 'phone', key: 'phone', width: 120, render: (v) => v || '-' },
    { title: 'Direccion', dataIndex: 'address', key: 'address', ellipsis: true, render: (v) => v || '-' },
    {
      title: 'Acciones',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: Supplier) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="Eliminar?" onConfirm={() => deleteMut.mutate(record.id)} okText="Si" cancelText="No">
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="end" style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} size="small">
          Nuevo
        </Button>
      </Row>
      <Table columns={columns} dataSource={(data ?? []) as Supplier[]} rowKey="id" loading={isLoading} size="small" pagination={false} />
      <Modal
        title={editingId ? 'Editar Proveedor' : 'Nuevo Proveedor'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={close}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createMut.isPending || updateMut.isPending}
        width={450}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="ruc" label="RUC">
            <Input />
          </Form.Item>
          <Form.Item>
            <Button
              type="default"
              icon={lookupLoading ? <LoadingOutlined /> : <SearchOutlined />}
              onClick={handleLookup}
              disabled={!canLookup || lookupLoading}
              loading={lookupLoading}
              size="small"
            >
              Consultar SUNAT
            </Button>
          </Form.Item>
          <Form.Item name="business_name" label="Razon Social" rules={[{ required: true, message: 'Requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="city" label="Ciudad">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="Telefono">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input />
          </Form.Item>
          <Form.Item name="address" label="Direccion">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

/* ============================================================
   Settings Page
   ============================================================ */
export default function Settings() {
  const brandColumns: ColumnsType<Brand> = [
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    {
      title: 'Estado',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Activo' : 'Inactivo'}</Tag>,
    },
  ];

  const categoryColumns: ColumnsType<Category> = [
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    {
      title: 'Estado',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Activo' : 'Inactivo'}</Tag>,
    },
  ];

  const warehouseColumns: ColumnsType<Warehouse> = [
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    { title: 'Direccion', dataIndex: 'address', key: 'address', render: (v) => v || '-' },
    {
      title: 'Estado',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Activo' : 'Inactivo'}</Tag>,
    },
  ];

  const seriesColumns: ColumnsType<DocumentSeries> = [
    { title: 'Tipo', dataIndex: 'doc_type', key: 'doc_type', width: 100 },
    { title: 'Serie', dataIndex: 'series', key: 'series', width: 100 },
    { title: 'Sig. Numero', dataIndex: 'next_number', key: 'next_number', width: 120 },
    {
      title: 'Estado',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Activo' : 'Inactivo'}</Tag>,
    },
  ];

  const tabItems = [
    {
      key: 'brands',
      label: 'Marcas',
      children: (
        <CrudTab<Brand>
          queryKey="brands"
          fetchFn={getBrands}
          createFn={createBrand}
          updateFn={updateBrand}
          deleteFn={deleteBrand}
          columns={brandColumns}
          title="Marca"
          onEdit={(record, form) => form.setFieldsValue({ name: record.name })}
          formFields={
            <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'Requerido' }]}>
              <Input />
            </Form.Item>
          }
        />
      ),
    },
    {
      key: 'categories',
      label: 'Categorias',
      children: (
        <CrudTab<Category>
          queryKey="categories"
          fetchFn={getCategories}
          createFn={createCategory}
          updateFn={updateCategory}
          deleteFn={deleteCategory}
          columns={categoryColumns}
          title="Categoria"
          onEdit={(record, form) => form.setFieldsValue({ name: record.name })}
          formFields={
            <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'Requerido' }]}>
              <Input />
            </Form.Item>
          }
        />
      ),
    },
    {
      key: 'warehouses',
      label: 'Almacenes',
      children: (
        <CrudTab<Warehouse>
          queryKey="warehouses"
          fetchFn={getWarehouses}
          createFn={createWarehouse}
          updateFn={updateWarehouse}
          deleteFn={deleteWarehouse}
          columns={warehouseColumns}
          title="Almacen"
          onEdit={(record, form) => form.setFieldsValue({ name: record.name, address: record.address })}
          formFields={
            <>
              <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'Requerido' }]}>
                <Input />
              </Form.Item>
              <Form.Item name="address" label="Direccion">
                <Input />
              </Form.Item>
            </>
          }
        />
      ),
    },
    {
      key: 'suppliers',
      label: 'Proveedores',
      children: <SupplierTab />,
    },
    {
      key: 'series',
      label: 'Series de Documentos',
      children: (
        <CrudTab<DocumentSeries>
          queryKey="doc-series"
          fetchFn={getDocumentSeries}
          createFn={createDocumentSeries}
          updateFn={updateDocumentSeries}
          deleteFn={async () => { message.info('No se puede eliminar series'); }}
          columns={seriesColumns}
          title="Serie"
          onEdit={(record, form) =>
            form.setFieldsValue({
              doc_type: record.doc_type,
              series: record.series,
              next_number: record.next_number,
            })
          }
          formFields={
            <>
              <Form.Item name="doc_type" label="Tipo Documento" rules={[{ required: true, message: 'Requerido' }]}>
                <Select
                  options={[
                    { value: 'BOLETA', label: 'Boleta' },
                    { value: 'FACTURA', label: 'Factura' },
                  ]}
                />
              </Form.Item>
              <Form.Item name="series" label="Serie" rules={[{ required: true, message: 'Requerido' }]}>
                <Input placeholder="Ej: B005" />
              </Form.Item>
              <Form.Item name="next_number" label="Siguiente Numero" rules={[{ required: true, message: 'Requerido' }]}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </>
          }
        />
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>Configuracion</Title>
      <Tabs items={tabItems} />
    </div>
  );
}
