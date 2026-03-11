import { useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  message,
  Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getTrabajadores,
  createTrabajador,
  updateTrabajador,
  deleteTrabajador,
} from '../../api/trabajadores';
import type { Trabajador } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import useEnterNavigation from '../../hooks/useEnterNavigation';

const { Title } = Typography;

const CARGO_OPTIONS = [
  { value: 'VENDEDOR', label: 'Vendedor' },
  { value: 'ALMACEN', label: 'Almacen' },
  { value: 'ADMINISTRACION', label: 'Administracion' },
  { value: 'DELIVERY', label: 'Delivery' },
  { value: 'PRODUCCION', label: 'Produccion' },
  { value: 'OTRO', label: 'Otro' },
];

const CARGO_COLORS: Record<string, string> = {
  VENDEDOR: 'blue',
  ALMACEN: 'orange',
  ADMINISTRACION: 'purple',
  DELIVERY: 'cyan',
  PRODUCCION: 'green',
  OTRO: 'default',
};

export default function TrabajadorList() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Trabajador | null>(null);
  const [form] = Form.useForm();
  const enterNavRef = useEnterNavigation(() => handleSubmit());

  const { data: trabajadores, isLoading } = useQuery({
    queryKey: ['trabajadores'],
    queryFn: getTrabajadores,
  });

  const createMutation = useMutation({
    mutationFn: createTrabajador,
    onSuccess: () => {
      message.success('Trabajador creado');
      queryClient.invalidateQueries({ queryKey: ['trabajadores'] });
      closeModal();
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Error al crear trabajador');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateTrabajador(id, data),
    onSuccess: () => {
      message.success('Trabajador actualizado');
      queryClient.invalidateQueries({ queryKey: ['trabajadores'] });
      closeModal();
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Error al actualizar trabajador');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTrabajador,
    onSuccess: () => {
      message.success('Trabajador eliminado');
      queryClient.invalidateQueries({ queryKey: ['trabajadores'] });
    },
    onError: () => message.error('Error al desactivar trabajador'),
  });

  const openCreate = () => {
    setEditingItem(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (item: Trabajador) => {
    setEditingItem(item);
    form.setFieldsValue({
      full_name: item.full_name,
      dni: item.dni,
      phone: item.phone,
      cargo: item.cargo,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingItem(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingItem) {
        updateMutation.mutate({ id: editingItem.id, data: values });
      } else {
        createMutation.mutate(values);
      }
    } catch {
      // validation failed
    }
  };

  const columns: ColumnsType<Trabajador> = [
    { title: 'Nombre', dataIndex: 'full_name', key: 'full_name', ellipsis: true },
    { title: 'DNI', dataIndex: 'dni', key: 'dni', width: 120 },
    { title: 'Telefono', dataIndex: 'phone', key: 'phone', width: 120, render: (v) => v || '-' },
    {
      title: 'Cargo',
      dataIndex: 'cargo',
      key: 'cargo',
      width: 140,
      render: (cargo: string) => (
        <Tag color={CARGO_COLORS[cargo] || 'default'}>{cargo}</Tag>
      ),
    },
    {
      title: 'Estado',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? 'Activo' : 'Inactivo'}</Tag>
      ),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: Trabajador) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm
            title="Eliminar trabajador?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Si"
            cancelText="No"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Trabajadores</Title>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo Trabajador
          </Button>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={trabajadores ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={false}
      />

      <Modal
        title={editingItem ? 'Editar Trabajador' : 'Nuevo Trabajador'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={closeModal}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnClose
      >
        <div ref={enterNavRef}>
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item
              name="full_name"
              label="Nombre Completo"
              rules={[{ required: true, message: 'Requerido' }]}
            >
              <Input />
            </Form.Item>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item
                  name="dni"
                  label="DNI"
                >
                  <Input maxLength={20} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="phone" label="Telefono">
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="cargo"
              label="Cargo"
              rules={[{ required: true, message: 'Requerido' }]}
            >
              <Select placeholder="Seleccionar" options={CARGO_OPTIONS} />
            </Form.Item>
          </Form>
        </div>
      </Modal>
    </div>
  );
}
